"""Evalúa la recuperación sobre el banco de pruebas (sin LLM).

Uso:
    uv run python -m gamerag.evaluation.retrieval zelda1
    uv run python -m gamerag.evaluation.retrieval zelda1 --chunker fixed --depth 20

Guarda en eval/results/<fecha>_<juego>_bm25-<chunker>.json las métricas agregadas y, por caso,
los candidatos recuperados con su score y relevancia (el curso pide guardar los candidatos,
no solo el resultado, para poder diagnosticar fallas).
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from gamerag.evaluation.cases import EvalCase, load_cases, parts_found
from gamerag.evaluation.metrics import coverage_at_k, mean, precision_at_k, recall_at_k, reciprocal_rank
from gamerag.retrieval.bm25 import BM25Index, Hit, load_chunks
from gamerag.settings import get_settings

KS = (1, 3, 5, 10)
RETRIEVAL_CATEGORIES = {"direct", "paraphrase", "exact_id", "compound", "ambiguous", "version"}


def evaluate_case(case: EvalCase, hits: list[Hit]) -> dict:
    parts = [parts_found(case, h.chunk) for h in hits]
    rels = [bool(p) for p in parts]
    first = next((h.rank for h, r in zip(hits, rels, strict=True) if r), None)
    return {
        "id": case.id,
        "category": case.category,
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


def run(game_id: str, chunker: str = "fixed", depth: int = 20) -> dict:
    s = get_settings()
    chunks = load_chunks(s.path(s.data_dir) / "processed" / game_id / f"chunks.{chunker}.jsonl")
    index = BM25Index(chunks)
    cases = [c for c in load_cases(s.root / "eval" / "cases.jsonl") if c.game == game_id]
    answerable = [c for c in cases if c.answerable and c.category in RETRIEVAL_CATEGORIES]

    rows = [evaluate_case(c, index.search(c.question, k=depth)) for c in answerable]
    by_category = {
        cat: aggregate([r for r in rows if r["category"] == cat])
        for cat in sorted({r["category"] for r in rows})
    }
    return {
        "run": {
            "game": game_id, "retriever": "bm25", "chunker": chunks[0].chunker, "depth": depth,
            "bm25": {"k1": index.k1, "b": index.b}, "n_chunks": len(chunks),
            "date": datetime.now(UTC).isoformat(timespec="seconds"),
            "cases_total": len(cases), "cases_evaluated": len(rows),
            "cases_skipped": [c.id for c in cases if c not in answerable],
        },
        "overall": aggregate(rows),
        "by_category": by_category,
        "cases": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("game_id")
    ap.add_argument("--chunker", default="fixed", help="sufijo del archivo de chunks (chunks.<chunker>.jsonl)")
    ap.add_argument("--depth", type=int, default=20, help="candidatos guardados por caso")
    args = ap.parse_args()

    report = run(args.game_id, args.chunker, args.depth)
    s = get_settings()
    out_dir = s.root / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    out = out_dir / f"{stamp}_{args.game_id}_bm25-{args.chunker}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")

    o = report["overall"]
    print(f"{args.game_id} · bm25 · {report['run']['chunker']} · {o['n']} casos")
    print(f"  Recall@1 {o['recall@1']:.2f}  Recall@3 {o['recall@3']:.2f}  Recall@5 {o['recall@5']:.2f}  "
          f"MRR {o['mrr']:.2f}  Coverage@5 {o['coverage@5']:.2f}")
    for cat, m in report["by_category"].items():
        print(f"  {cat:11} n={m['n']}  R@5 {m['recall@5']:.2f}  MRR {m['mrr']:.2f}  Cov@5 {m['coverage@5']:.2f}")
    for r in report["cases"]:
        mark = "✓" if r["recall@5"] else "✗"
        print(f"  {mark} {r['id']:22} first_relevant={r['first_relevant_rank']}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
