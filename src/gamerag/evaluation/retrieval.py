"""Evalúa la recuperación sobre el banco de pruebas (sin LLM).

Uso:
    uv run python -m gamerag.evaluation.retrieval zelda1                               # BM25
    uv run python -m gamerag.evaluation.retrieval zelda1 --retriever dense --model bge-small-en
    uv run python -m gamerag.evaluation.retrieval zelda1 --retriever hybrid --model e5-small-multi

`dense` e `hybrid` requieren el extra `semantic` (`uv sync --extra semantic`).

Guarda en eval/results/<fecha>_<juego>_<variante>.json las métricas agregadas y, por caso, los
candidatos recuperados con su score y relevancia (el curso pide guardar los candidatos, no solo el
resultado, para poder diagnosticar fallas).
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime

from gamerag.evaluation.cases import EvalCase, load_cases, parts_found
from gamerag.evaluation.metrics import coverage_at_k, mean, precision_at_k, recall_at_k, reciprocal_rank
from gamerag.retrieval.bm25 import Hit, load_chunks
from gamerag.retrieval.factory import make_retriever
from gamerag.retrieval.hybrid import Retriever
from gamerag.settings import get_settings

KS = (1, 3, 5, 10)
RETRIEVAL_CATEGORIES = {"direct", "paraphrase", "exact_id", "compound", "ambiguous", "version", "robustness"}
# Las 18 preguntas con respuesta de la distribución del curso (§8); sobre estas se fijaron la línea base y ADR-0009.
COURSE_CATEGORIES = {"direct", "paraphrase", "exact_id", "compound", "ambiguous", "version"}


def evaluate_case(case: EvalCase, hits: list[Hit]) -> dict:
    parts = [parts_found(case, h.chunk) for h in hits]
    rels = [bool(p) for p in parts]
    first = next((h.rank for h, r in zip(hits, rels, strict=True) if r), None)
    return {
        "id": case.id,
        "category": case.category,
        "author": case.author,
        "question": case.question,
        "first_relevant_rank": first,
        **{f"recall@{k}": recall_at_k(rels, k) for k in KS},
        **{f"precision@{k}": precision_at_k(rels, k) for k in KS},
        **{f"coverage@{k}": coverage_at_k(parts, len(case.evidence), k) for k in KS},
        "rr": reciprocal_rank(rels),
        "candidates": [
            {"rank": h.rank, "score": round(h.score, 4), "chunk_id": h.chunk.chunk_id,
             "section": h.chunk.section, "relevant": r}
            for h, r in zip(hits, rels, strict=True)
        ],
    }


def aggregate(rows: list[dict]) -> dict:
    out = {"n": len(rows), "mrr": round(mean([r["rr"] for r in rows]), 4)}
    for k in KS:
        for m in ("recall", "precision", "coverage"):
            out[f"{m}@{k}"] = round(mean([r[f"{m}@{k}"] for r in rows]), 4)
    return out


def evaluate(retriever: Retriever, cases: list[EvalCase], depth: int = 20) -> tuple[list[dict], list[float]]:
    rows, latencies = [], []
    for c in cases:
        t = time.perf_counter()
        hits = retriever.search(c.question, k=depth)
        latencies.append(time.perf_counter() - t)
        rows.append(evaluate_case(c, hits))
    return rows, latencies


def run(game_id: str, retriever_name: str = "bm25", model_key: str | None = None,
        chunker: str = "fixed", depth: int = 20, reranker: str | None = None, expand: bool = False) -> dict:
    s = get_settings()
    chunks = load_chunks(s.path(s.data_dir) / "processed" / game_id / f"chunks.{chunker}.jsonl")
    t = time.perf_counter()
    retriever = make_retriever(retriever_name, chunks, s, model_key, reranker, expand)
    setup_s = time.perf_counter() - t
    cases = [c for c in load_cases(s.root / "eval" / "cases.jsonl") if c.game == game_id]
    answerable = [c for c in cases if c.answerable and c.category in RETRIEVAL_CATEGORIES]

    rows, lat = evaluate(retriever, answerable, depth)
    lat_sorted = sorted(lat)
    model = None if retriever_name == "bm25" else (model_key or s.embedding_model)
    return {
        "run": {
            "game": game_id, "retriever": retriever_name, "embedding_model": model,
            "reranker": reranker, "expand": expand,
            "chunker": chunks[0].chunker, "depth": depth, "n_chunks": len(chunks),
            "date": datetime.now(UTC).isoformat(timespec="seconds"),
            "cases_total": len(cases), "cases_evaluated": len(rows),
            "cases_skipped": [c.id for c in cases if c not in answerable],
            "setup_seconds": round(setup_s, 2),
            "latency_ms": {"mean": round(1000 * mean(lat), 1),
                           "p95": round(1000 * lat_sorted[int(0.95 * (len(lat_sorted) - 1))], 1)},
        },
        "overall": aggregate(rows),
        # Subconjunto del curso (18 casos): comparable con la línea base y ADR-0009.
        "course": aggregate([r for r in rows if r["category"] in COURSE_CATEGORIES]),
        # Conjunto independiente: preguntas del equipo, escritas sin ver el corpus ni el sistema.
        "team": aggregate([r for r in rows if r["author"] == "team"]),
        "by_category": {cat: aggregate([r for r in rows if r["category"] == cat])
                        for cat in sorted({r["category"] for r in rows})},
        "cases": rows,
    }


def variant_name(retriever: str, model: str | None, chunker: str, reranker: str | None = None,
                 expand: bool = False) -> str:
    name = f"{retriever}-{model}-{chunker}" if model else f"{retriever}-{chunker}"
    name = f"{name}-qx" if expand else name
    return f"{name}-rr-{reranker}" if reranker else name


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("game_id")
    ap.add_argument("--retriever", choices=["bm25", "dense", "hybrid"], default="bm25")
    ap.add_argument("--model", default=None, help="clave del modelo de embeddings (dense/hybrid)")
    ap.add_argument("--chunker", default="fixed", help="sufijo del archivo de chunks (chunks.<chunker>.jsonl)")
    ap.add_argument("--depth", type=int, default=20, help="candidatos guardados por caso")
    ap.add_argument("--reranker", default=None, help="clave del reranker (segunda etapa), p. ej. minilm-en")
    ap.add_argument("--expand", action="store_true", help="multi-consulta con el glosario del juego")
    args = ap.parse_args()

    report = run(args.game_id, args.retriever, args.model, args.chunker, args.depth, args.reranker, args.expand)
    s = get_settings()
    out_dir = s.root / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    name = variant_name(args.retriever, report["run"]["embedding_model"], args.chunker, args.reranker, args.expand)
    out = out_dir / f"{datetime.now(UTC):%Y-%m-%d}_{args.game_id}_{name}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")

    r = report["run"]
    print(f"{args.game_id} · {name} · latencia media {r['latency_ms']['mean']} ms")
    for label in ("course", "team", "overall"):
        o = report[label]
        print(f"  {label:7} n={o['n']:2}  Recall@1 {o['recall@1']:.2f}  Recall@3 {o['recall@3']:.2f}  "
              f"Recall@5 {o['recall@5']:.2f}  MRR {o['mrr']:.2f}  Coverage@5 {o['coverage@5']:.2f}")
    for cat, m in report["by_category"].items():
        print(f"  {cat:11} n={m['n']}  R@5 {m['recall@5']:.2f}  MRR {m['mrr']:.2f}  Cov@5 {m['coverage@5']:.2f}")
    for row in report["cases"]:
        print(f"  {'✓' if row['recall@5'] else '✗'} {row['id']:22} first_relevant={row['first_relevant_rank']}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
