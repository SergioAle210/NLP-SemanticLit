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
from datetime import UTC, datetime
from pathlib import Path

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
    before = ledger.summary()
    t = time.perf_counter()
    try:
        answer, trace = pipe.ask(case.question, case.game, profile)
        error = None
    except BudgetExceeded:
        raise
    except Exception as exc:  # noqa: BLE001 - un caso roto no debe tirar toda la corrida
        answer, trace, error = None, None, f"{type(exc).__name__}: {exc}"
    latency = time.perf_counter() - t
    if store is not None and trace is not None:
        store.log_trace(trace)
    after = ledger.summary()
    row = {
        "id": case.id, "category": case.category, "game": case.game, "answerable": case.answerable,
        "question": case.question, "error": error, "latency_s": round(latency, 3),
        "input_tokens": after["input_tokens"] - before["input_tokens"],
        "output_tokens": after["output_tokens"] - before["output_tokens"],
        "cost_usd": round(after["spent_usd"] - before["spent_usd"], 6),
    }
    if answer is None:
        return row
    ctx = [chunks[i] for i in trace.context if i in chunks]
    cited = [chunks[s.chunk_id] for s in answer.sources if s.chunk_id in chunks]
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
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--retriever", default="bm25", choices=["bm25", "dense", "hybrid"])
    ap.add_argument("--generator", default="haiku", choices=["extractive", "haiku"])
    ap.add_argument("--graph", action="store_true")
    ap.add_argument("--evidence", action="store_true", help="evaluador de evidencia + reescritura (implica --graph)")
    ap.add_argument("--max-cases", type=int, default=None, help="limita la cantidad de casos (prueba barata)")
    ap.add_argument("--label", default=None)
    ap.add_argument("--chunker", default=None, help="p. ej. structural-multi (corpus con varias wikis)")
    ap.add_argument("--cases", default="eval/cases.jsonl", help="banco de casos (p. ej. eval/cases_hard.jsonl)")
    ap.add_argument("--planner", action="store_true", help="descomposición de consulta (implica --graph)")
    ap.add_argument("--notes", action="store_true", help="indexar las notas de data/memory/<juego>/")
    ap.add_argument("--secondary", action="store_true", help="wikis extra como segunda busqueda (implica --evidence)")
    ap.add_argument("--secondary-mode", choices=["append", "mixed"], default="append",
                    help="append: suma chunks extra; mixed: reemplaza el contexto con un indice mezclado")
    ap.add_argument("--only-game", nargs="*", default=[], help="armar solo estos juegos")
    ap.add_argument("--split", choices=["train", "test"], default=None, help="solo la partición indicada")
    ap.add_argument("--trace-db", default=None, help="SQLite donde guardar las trazas (entrada del dreaming)")
    ap.add_argument("--profile", default=None, help="fuerza un perfil para todos los casos (p. ej. novato)")
    ap.add_argument("--mode", default=None, choices=["always", "on_abstain"], help="modo del evaluador de evidencia")
    args = ap.parse_args()

    base = get_settings()
    s = Settings(root=base.root, retriever=args.retriever, generator=args.generator, router=True,
                 use_graph=args.graph or args.evidence or args.planner or args.secondary,
                 evidence_eval=args.evidence or args.secondary, secondary_search=args.secondary,
                 only_games=args.only_game,
                 secondary_mode=args.secondary_mode,
                 secondary_k=5 if args.secondary_mode == "mixed" else 3,
                 planner=args.planner, memory_notes=args.notes,
                 llm_cache=False,  # sin caché: se mide el costo real de cada pregunta
                 **({"chunker": args.chunker} if args.chunker else {}),
                 **({"evidence_mode": args.mode} if args.mode else {}))
    pipe = build_pipeline(s)
    games = load_all_games(s.path(s.games_config_dir))
    profiles = load_profiles(s.path(s.seed_profiles), games)
    cases = [c for c in load_cases(s.root / args.cases) if c.game in pipe.retrievers]
    if args.split:
        cases = [c for c in cases if split_of(c.id) == args.split]
    if args.max_cases:
        cases = cases[: args.max_cases]
    chunks = _chunk_index(pipe, s)
    ledger = LLMClient(s).ledger
    store = Store(s.path(Path(args.trace_db))) if args.trace_db else None

    rows: list[dict] = []
    for c in cases:
        rows.append(run_case(pipe, c, profiles[args.profile or c.profile], chunks, ledger, store))
        print(f"  {c.id:24} {'abst' if rows[-1].get('abstained') else 'ans ':4} "
              f"ctx={rows[-1].get('ctx_hit')} ${rows[-1]['cost_usd']:.5f} {rows[-1]['latency_s']:.2f}s"
              f"{' ERR ' + rows[-1]['error'] if rows[-1]['error'] else ''}")

    label = args.label or f"{args.retriever}-{args.generator}{'-graph' if args.graph else ''}" \
                          f"{'-evidence' if args.evidence else ''}"
    report = {
        "run": {"label": label, "retriever": args.retriever, "generator": args.generator, "graph": s.use_graph,
                "evidence": args.evidence, "model": s.llm_model, "n_cases": len(cases),
                "date": datetime.now(UTC).isoformat(timespec="seconds")},
        "overall": _agg(rows),
        "by_category": {cat: _agg([r for r in rows if r["category"] == cat]) for cat in
                        sorted({r["category"] for r in rows})},
        "cases": rows,
    }
    out_dir = s.root / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{datetime.now(UTC):%Y-%m-%d}_e2e_{label}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(json.dumps(report["overall"], indent=1))
    print(f"-> {out}   (gasto acumulado del proyecto: ${ledger.spent():.4f})")


if __name__ == "__main__":
    main()
