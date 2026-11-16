"""Evaluación de extremo a extremo del pipeline (con LLM): contexto entregado, abstención, citas, costo.

Uso (gasta tokens reales; respeta los topes de `gamerag.llm`):
    uv run python -m gamerag.evaluation.e2e --retriever bm25 --generator haiku
    uv run python -m gamerag.evaluation.e2e --retriever bm25 --generator haiku --graph --evidence

Por caso se guarda el contexto entregado, la respuesta, las citas, los reintentos del evaluador, tokens,
costo y latencia. Métricas agregadas:
- `ctx_recall`: el contexto entregado contiene evidencia esperada (casos con respuesta y de recuperación).
- `abstention_ok`: abstiene exactamente cuando el caso no tiene respuesta.
- `cite_precision`: fracción de citas que son chunks relevantes (casos con respuesta y de recuperación).
- costo y tokens por pregunta, latencia media y P95.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from gamerag.evaluation.artifacts import (
    corpus_fingerprint,
    evidence_chunks,
    run_metadata,
    usage_from_calls,
    write_report,
)
from gamerag.evaluation.cases import EvalCase, load_cases, parts_found
from gamerag.evaluation.metrics import mean
from gamerag.evaluation.retrieval import RETRIEVAL_CATEGORIES
from gamerag.explain import explain
from gamerag.games import load_all_games
from gamerag.guardrails.provenance import leaked_notes
from gamerag.llm import BudgetExceeded, LLMClient
from gamerag.pipeline import build_pipeline
from gamerag.progress.models import load_profiles
from gamerag.retrieval.bm25 import load_chunks
from gamerag.settings import Settings, get_settings
from gamerag.store import Store
from gamerag.telemetry import request_scope


def _chunk_index(pipe, s: Settings) -> dict:
    out: dict = {}
    for game in pipe.retrievers:
        path = s.path(s.data_dir) / "processed" / game / f"chunks.{s.chunker}.jsonl"
        out.update({c.chunk_id: c for c in load_chunks(path)})
        multi = path.with_name(f"chunks.{s.chunker}-multi.jsonl")
        if s.secondary_search and multi.exists():  # los chunks de la segunda busqueda tambien entran al analisis
            out.update({c.chunk_id: c for c in load_chunks(multi)})
        notes = s.path(s.memory_dir) / game / "notes.jsonl"
        if s.memory_notes and notes.exists():
            out.update({c.chunk_id: c for c in load_chunks(notes)})
    return out


def split_of(case_id: str) -> str:
    """Partición estable train/test por caso (el dreaming aprende de 'train'; se mide en 'test')."""
    return "train" if int(hashlib.sha256(case_id.encode()).hexdigest(), 16) % 2 == 0 else "test"


def run_case(pipe, case: EvalCase, profile, chunks: dict, ledger, store=None) -> dict:
    t = time.perf_counter()
    with request_scope() as capture:
        try:
            answer, trace = pipe.ask(case.question, case.game, profile)
            error = None
        except BudgetExceeded as exc:
            answer, trace, error = None, None, f"BudgetExceeded: {exc}"
        except Exception as exc:  # noqa: BLE001 - un caso roto no debe tirar toda la corrida
            answer, trace, error = None, None, f"{type(exc).__name__}: {exc}"
    latency = time.perf_counter() - t
    if store is not None and trace is not None:
        store.log_trace(trace)
    calls = list(capture.calls)
    row = {
        "id": case.id, "category": case.category, "game": case.game, "answerable": case.answerable,
        "question": case.question, "error": error, "latency_s": round(latency, 3),
        "trace_id": capture.trace_id, "player_profile": profile.model_dump(mode="json"),
        "llm_calls": calls, "degradations": list(capture.degradations), "stages": list(capture.stages),
        **usage_from_calls(calls),
    }
    if answer is None:
        return row
    row.update({"context": trace.context, "sources": [s.chunk_id for s in answer.sources],
                "citations": [source.model_dump(mode="json") for source in answer.sources],
                "final_evidence": [doc.model_dump(mode="json") for doc in trace.final_evidence],
                "final_answer": answer.model_dump(mode="json")})
    try:
        ctx = evidence_chunks(row, chunks)
        cited = evidence_chunks(row, chunks, cited=True)
    except ValueError as exc:
        row["error"] = f"EvidenceContractError: {exc}"
        return row
    evaluable = case.answerable and case.category in RETRIEVAL_CATEGORIES
    notes_in_ctx = [c.chunk_id for c in ctx if c.kind == "note"]
    base_filters = [f for f in pipe.access_filters if f.name != "provenance"]
    row.update({
        "notes_in_context": notes_in_ctx,
        "secondary": trace.secondary,
        "note_leaks": leaked_notes(ctx, chunks, base_filters, profile, case.game),
        "subqueries": [q["query"] for q in trace.subqueries],
        "answer": answer.answer, "abstained": answer.abstained, "outcome": trace.outcome,
        "tool_used": answer.tool_used, "route": trace.route,
        "explanation_complete": explain(trace, answer)["complete"],
        "context": trace.context, "sources": [s.chunk_id for s in answer.sources],
        "rewrites": [e["rewrite"] for e in trace.evidence if not e["sufficient"]],
        "retrieval_rewrite_count": sum(not e["sufficient"] and bool(e.get("rewrite")) for e in trace.evidence),
        "evidence_trace": trace.evidence,
        "abstention_ok": answer.abstained == (not case.answerable),
        "ctx_hit": any(parts_found(case, c) for c in ctx) if evaluable else None,
        # cobertura multi-salto: partes de evidencia presentes en la unión del contexto entregado
        "ctx_coverage": (len(set().union(*(parts_found(case, c) for c in ctx))) / len(case.evidence)
                         if ctx else 0.0) if evaluable else None,
        "cite_precision": (mean([bool(parts_found(case, c)) for c in cited]) if cited else 0.0)
        if evaluable and not answer.abstained else None,
    })
    return row


def _agg(rows: list[dict]) -> dict:
    ok = [r for r in rows if not r.get("error")]

    def avg(key):
        vals = [float(r[key]) for r in ok if r.get(key) is not None]
        return round(mean(vals), 4) if vals else None

    lat = sorted(r["latency_s"] for r in rows)
    return {
        "n": len(rows), "errors": len(rows) - len(ok),
        "ctx_recall": avg("ctx_hit"), "ctx_coverage": avg("ctx_coverage"),
        "ctx_hit_rate": avg("ctx_hit"),
        "abstention_ok": avg("abstention_ok"), "cite_precision": avg("cite_precision"),
        "explainable_rate": round(mean([bool(r.get("explanation_complete")) for r in ok]), 4) if ok else None,
        "notes_used_rate": round(mean([bool(r.get("notes_in_context")) for r in ok]), 4) if ok else None,
        "secondary_rate": round(mean([bool(r.get("secondary")) for r in ok]), 4) if ok else None,
        "note_leaks": sum(len(r.get("note_leaks", [])) for r in ok),
        "decomposed_rate": round(mean([len(r.get("subqueries", [])) > 1 for r in ok]), 4) if ok else None,
        "rewrite_rate": round(mean([bool(r.get("rewrites")) for r in ok]), 4) if ok else None,
        "cost_per_q_usd": round(mean([r["cost_usd"] for r in rows]), 6) if rows else None,
        "tokens_per_q": round(mean([r["input_tokens"] + r["output_tokens"] for r in rows]), 1) if rows else None,
        "latency_mean_s": round(mean(lat), 3) if lat else None,
        "latency_p95_s": lat[int(0.95 * (len(lat) - 1))] if lat else None,
        "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 5),
        "llm_calls": sum(r.get("llm_call_count", 0) for r in rows),
        "llm_errors": sum(r.get("llm_error_count", 0) for r in rows),
        "http_retries": sum(r.get("http_retry_count", 0) for r in rows),
        "usage_unknown_calls": sum(r.get("usage_unknown_calls", 0) for r in rows),
        "degraded_requests": sum(bool(r.get("degradations")) for r in rows),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serving-profile", choices=["base", "full"],
                    help="preset servido; distinto del perfil del jugador")
    ap.add_argument("--retriever", default=None, choices=["bm25", "dense", "hybrid"])
    ap.add_argument("--generator", default=None, choices=["extractive", "haiku"])
    ap.add_argument("--graph", action="store_true", default=None)
    ap.add_argument("--evidence", action="store_true", default=None,
                    help="evaluador de evidencia + reescritura (implica --graph)")
    ap.add_argument("--max-cases", type=int, default=None, help="limita la cantidad de casos (prueba barata)")
    ap.add_argument("--label", default=None)
    ap.add_argument("--quiet", action="store_true", help="imprime solo el resumen y la ruta del artefacto")
    ap.add_argument("--chunker", default=None, help="p. ej. structural-multi (corpus con varias wikis)")
    ap.add_argument("--cases", default="eval/cases.jsonl", help="banco de casos (p. ej. eval/cases_hard.jsonl)")
    ap.add_argument("--planner", action="store_true", default=None, help="descomposición (implica --graph)")
    ap.add_argument("--notes", action="store_true", default=None, help="indexar notas de data/memory/<juego>/")
    ap.add_argument("--secondary", action="store_true", default=None, help="segunda búsqueda (implica --evidence)")
    ap.add_argument("--secondary-mode", choices=["append", "mixed"], default=None,
                    help="append: suma chunks extra; mixed: reemplaza el contexto con un indice mezclado")
    ap.add_argument("--only-game", nargs="*", default=[], help="armar solo estos juegos")
    ap.add_argument("--split", choices=["train", "test"], default=None, help="solo la partición indicada")
    ap.add_argument("--trace-db", default=None, help="SQLite donde guardar las trazas (entrada del dreaming)")
    ap.add_argument("--profile", default=None, help="fuerza un perfil para todos los casos (p. ej. novato)")
    ap.add_argument("--mode", default=None, choices=["always", "on_abstain"], help="modo del evaluador de evidencia")
    args = ap.parse_args()

    base = get_settings()
    overrides = {"root": base.root, "router": True, "only_games": args.only_game, "llm_cache": False}
    if args.serving_profile:
        overrides["profile"] = args.serving_profile
    else:  # compatibilidad con los comandos históricos
        overrides.update(retriever=args.retriever or "bm25", generator=args.generator or "haiku",
                         use_graph=False, evidence_eval=False, secondary_search=False, planner=False,
                         memory_notes=False, secondary_mode="append", secondary_k=3)
    for arg, key in (("retriever", "retriever"), ("generator", "generator"), ("graph", "use_graph"),
                     ("evidence", "evidence_eval"), ("planner", "planner"), ("notes", "memory_notes"),
                     ("secondary", "secondary_search"), ("secondary_mode", "secondary_mode"),
                     ("chunker", "chunker"), ("mode", "evidence_mode")):
        if getattr(args, arg) is not None:
            overrides[key] = getattr(args, arg)
    if args.graph or args.evidence or args.planner or args.secondary:
        overrides["use_graph"] = True
    if args.secondary:
        overrides["evidence_eval"] = True
    if args.secondary_mode:
        overrides["secondary_k"] = 5 if args.secondary_mode == "mixed" else 3
    s = Settings(**overrides)
    label = args.label or f"{s.retriever}-{s.generator}{'-graph' if s.use_graph else ''}" \
                          f"{'-evidence' if s.evidence_eval else ''}"
    metadata = run_metadata(s, label=label, dataset=s.root / args.cases)
    pipe = build_pipeline(s)
    games = load_all_games(s.path(s.games_config_dir))
    profiles = load_profiles(s.path(s.seed_profiles), games)
    cases = [c for c in load_cases(s.root / args.cases) if c.game in pipe.retrievers]
    if args.split:
        cases = [c for c in cases if split_of(c.id) == args.split]
    if args.max_cases:
        cases = cases[: args.max_cases]
    chunks = _chunk_index(pipe, s)
    metadata["corpus_sha256"] = corpus_fingerprint(chunks)
    ledger = LLMClient(s).ledger
    store = Store(s.path(Path(args.trace_db))) if args.trace_db else None

    rows: list[dict] = []
    for c in cases:
        rows.append(run_case(pipe, c, profiles[args.profile or c.profile], chunks, ledger, store))
        if not args.quiet:
            print(f"  {c.id:24} {'abst' if rows[-1].get('abstained') else 'ans ':4} "
                  f"ctx={rows[-1].get('ctx_hit')} ${rows[-1]['cost_usd']:.5f} {rows[-1]['latency_s']:.2f}s"
                  f"{' ERR ' + rows[-1]['error'] if rows[-1]['error'] else ''}")
        if (rows[-1].get("error") or "").startswith("BudgetExceeded:"):
            break

    ending_hash = run_metadata(s, label=label)["implementation_sha256"]
    report = {
        "schema_version": 2,
        "run": {**metadata, "implementation_sha256_end": ending_hash,
                "implementation_changed_during_run": ending_hash != metadata["implementation_sha256"],
                "retriever": s.retriever, "generator": s.generator, "graph": s.use_graph,
                "evidence": s.evidence_eval, "model": s.llm_model, "n_cases": len(rows),
                "selected_case_ids": [case.id for case in cases], "completed_case_ids": [row["id"] for row in rows],
                "split": args.split,
                "player_profile_override": args.profile,
                "latency_scope": "pipe.ask_only_excludes_bootstrap_and_model_loading",
                "percentile_method": "lower_order_statistic_floor_p_times_n_minus_1"},
        "overall": _agg(rows),
        "by_category": {cat: _agg([r for r in rows if r["category"] == cat]) for cat in
                        sorted({r["category"] for r in rows})},
        "cases": rows,
    }
    out = write_report(s.root / "eval" / "results", "e2e", report)
    print(json.dumps(report["overall"], indent=1))
    print(f"-> {out}   (gasto acumulado del proyecto: ${ledger.spent():.4f})")


if __name__ == "__main__":
    main()
