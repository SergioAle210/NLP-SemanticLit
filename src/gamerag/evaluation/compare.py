"""Comparación pareada de dos corridas de `evaluation.e2e` con métricas más finas que `ctx_recall`.

    uv run python -m gamerag.evaluation.compare eval/results/A.json eval/results/B.json --cases eval/cases.jsonl

`ctx_recall` se satura (el contexto casi siempre contiene *algo* relevante), así que además se mide, por caso:
- `ctx_mrr`: 1/posición del primer chunk relevante en el contexto entregado (qué tan arriba queda la evidencia);
- `ctx_coverage`: partes de evidencia cubiertas por el contexto (multi-salto);
- `n_ctx`: chunks entregados (menos = prompt más corto);
- `correct`: veredicto de un juez LLM (correcto=1, parcial=0.5, incorrecto=0) sobre la respuesta final, comparada
  con el comportamiento esperado del caso; un caso sin respuesta es correcto solo si el sistema se abstiene;
- tokens, costo, latencia, citas y sub-consultas (ya registrados por e2e).
Reporta las medias de cada corrida y, sobre los casos donde la corrida B usó notas, la diferencia pareada.
"""

from __future__ import annotations

import argparse
import json

from gamerag.evaluation.cases import EvalCase, load_cases, parts_found
from gamerag.evaluation.metrics import mean
from gamerag.llm import LLMClient
from gamerag.retrieval.bm25 import load_chunks
from gamerag.settings import get_settings

SYSTEM = (
    "You grade a game-assistant answer. Given the question, the expected behavior, and the answer, reply "
    "'correct' if the answer contains what the expected behavior asks for and nothing contradicting it; "
    "'partial' if it covers only part of it; 'wrong' otherwise (including refusing to answer when an answer "
    "was expected). Judge only against the expected behavior, not your own knowledge."
)
SCHEMA = {"type": "object", "properties": {"verdict": {"type": "string", "enum": ["correct", "partial", "wrong"]}},
          "required": ["verdict"], "additionalProperties": False}
SCORE = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}


def judge(llm: LLMClient, case: EvalCase, row: dict) -> float:
    if not case.answerable:
        return 1.0 if row.get("abstained") else 0.0
    if row.get("abstained") or row.get("error"):
        return 0.0
    user = (f"Question: {case.question}\nExpected behavior: {case.expected_behavior}\nAnswer: {row['answer']}")
    msg = llm.complete([{"role": "user", "content": user}], system=SYSTEM, max_tokens=60, run="judge",
                       output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}})
    return SCORE[json.loads(llm.text(msg))["verdict"]]


def enrich(rows: list[dict], cases: dict[str, EvalCase], chunks: dict, llm: LLMClient) -> list[dict]:
    out = []
    for r in rows:
        case = cases[r["id"]]
        ctx = [chunks[i] for i in r.get("context", []) if i in chunks]
        evaluable = case.answerable and case.category in {"direct", "paraphrase", "exact_id", "compound",
                                                          "ambiguous", "version", "robustness"}
        first = next((k for k, c in enumerate(ctx, 1) if parts_found(case, c)), None)
        out.append({**r, "correct": judge(llm, case, r), "n_ctx": len(ctx),
                    "ctx_mrr": (1 / first if first else 0.0) if evaluable else None,
                    "n_subq": len(r.get("subqueries", []))})
    return out


def _avg(rows: list[dict], key: str):
    vals = [float(r[key]) for r in rows if r.get(key) is not None]
    return round(mean(vals), 4) if vals else None


METRICS = ["correct", "ctx_mrr", "ctx_coverage", "cite_precision", "n_ctx", "input_tokens", "cost_usd", "latency_s"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--cases", default="eval/cases.jsonl")
    ap.add_argument("--used-key", default="notes_in_context", help="campo que marca los casos afectados (secondary)")
    args = ap.parse_args()

    s = get_settings()
    cases = {c.id: c for c in load_cases(s.root / args.cases)}
    chunks = {}
    for game in {c.game for c in cases.values()}:
        chunks |= {c.chunk_id: c for c in load_chunks(s.path(s.data_dir) / "processed" / game /
                                                      f"chunks.{s.chunker}.jsonl")}
        notes = s.path(s.memory_dir) / game / "notes.jsonl"
        if notes.exists():
            chunks |= {c.chunk_id: c for c in load_chunks(notes)}
    llm = LLMClient(s)
    runs = {}
    for label, path in (("A", args.a), ("B", args.b)):
        rows = json.loads((s.root / path).read_text(encoding="utf-8"))["cases"]
        runs[label] = {r["id"]: r for r in enrich(rows, cases, chunks, llm)}

    ids = [i for i in runs["A"] if i in runs["B"]]
    used = [i for i in ids if runs["B"][i].get(args.used_key)]
    print(f"A={args.a}\nB={args.b}   (casos={len(ids)}, B uso {args.used_key} en {len(used)})\n")
    print(f"{'metrica':16}{'A (todos)':>11}{'B (todos)':>11}{'A (c/notas)':>13}{'B (c/notas)':>13}{'delta':>8}")
    for m in METRICS:
        a_all, b_all = _avg([runs['A'][i] for i in ids], m), _avg([runs['B'][i] for i in ids], m)
        a_u, b_u = _avg([runs['A'][i] for i in used], m), _avg([runs['B'][i] for i in used], m)
        d = round(b_u - a_u, 4) if a_u is not None and b_u is not None else None
        print(f"{m:16}{a_all!s:>11}{b_all!s:>11}{a_u!s:>13}{b_u!s:>13}{d!s:>11}")
    better = [i for i in ids if runs["B"][i]["correct"] > runs["A"][i]["correct"]]
    worse = [i for i in ids if runs["B"][i]["correct"] < runs["A"][i]["correct"]]
    print(f"\ncorreccion B>A en {len(better)} casos {better}\ncorreccion B<A en {len(worse)} casos {worse}")


if __name__ == "__main__":
    main()
