"""Métricas de diagnóstico e interpretabilidad sobre los resultados de `evaluation.e2e` (sin red, sin costo).

Se calculan a partir del JSON de una corrida (por caso: contexto entregado, citas, respuesta, abstención) más el banco
de casos (evidencia esperada) y el índice de chunks (texto). Todas son deterministas y baratas, así que sirven como
**puerta de regresión** al cambiar el sistema (ver `scorecard.py`).

Recuperación (¿el contexto que recibe el generador contiene la evidencia?)
- `recall@k`, `mrr`, `ndcg@k`: relevancia binaria por chunk (definición de `cases.parts_found`), en el orden entregado.
- `coverage`: partes de evidencia cubiertas por la unión del contexto (preguntas compuestas).
- `noise`: fracción de chunks del contexto sin ninguna parte de evidencia (ruido que paga el generador en tokens).
- `redundancy`: similitud Jaccard media entre pares de chunks del contexto (alta = contexto repetitivo).

Atribución y fidelidad (¿la respuesta se apoya en lo que cita?)
- `cite_precision`: fracción de chunks citados que contienen evidencia.
- `cite_recall`: fracción de partes de evidencia cubiertas por los chunks citados.
- `groundedness`: apoyo léxico por oración: palabras de contenido de cada oración que aparecen en los chunks citados
  (o en el contexto si no cita). Aproximación determinista a la fidelidad; el juez LLM (`compare`) es la medida cara.
- `unsupported_rate`: fracción de oraciones con apoyo < 0.5.
- `novel_number_rate`: fracción de respuestas con algún número que no aparece en el contexto (señal de alucinación
  numérica, la más dañina en una guía de juego).

Abstención y calibración (¿sabe cuándo no sabe?)
- `abstain_precision/recall/f1`: la clase positiva es "abstenerse"; el ideal es abstenerse en las no respondibles.
- `false_abstain_rate`: respondibles en las que se abstuvo (utilidad perdida).
- `overconfident_rate`: no respondibles que se respondieron (el riesgo).
- `answered_without_evidence`: respondió una pregunta respondible sin tener la evidencia en el contexto (acierto por
  casualidad o por conocimiento del modelo; no es fundamentado).
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from statistics import mean

from gamerag.evaluation.cases import EvalCase, parts_found
from gamerag.ingest.models import Chunk

STOP = set("""the a an and or of to in on at for with from by is are was were be been it its this that these those
you your
can will not as if then than but so do does did how what which who when where why about into over after before also may
more most any each other such only just have has had they them their there here""".split())


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _content(text: str) -> set[str]:
    return {w for w in _tokens(text) if len(w) >= 4 and w not in STOP}


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(_tokens(s)) >= 4]


def ndcg_at_k(rels: list[bool], k: int) -> float:
    dcg = sum(1 / math.log2(i + 2) for i, r in enumerate(rels[:k]) if r)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(sum(rels), k)))
    return dcg / ideal if ideal else 0.0


def redundancy(chunks: list[Chunk]) -> float:
    sets = [_content(c.text) for c in chunks]
    pairs = [(a, b) for i, a in enumerate(sets) for b in sets[i + 1:] if a | b]
    return mean(len(a & b) / len(a | b) for a, b in pairs) if pairs else 0.0


def groundedness(answer: str, support: Iterable[Chunk]) -> tuple[float | None, float | None]:
    """(apoyo medio por oración, fracción de oraciones sin apoyo). None si no hay oraciones evaluables."""
    sup = set().union(*(_content(c.text) for c in support)) if support else set()
    scores = []
    for s in _sentences(answer):
        words = _content(s)
        if words:
            scores.append(len(words & sup) / len(words))
    if not scores:
        return None, None
    return mean(scores), mean(x < 0.5 for x in scores)


def novel_number(answer: str, context: Iterable[Chunk]) -> bool:
    nums = set(re.findall(r"\d+", answer))
    ctx = set(re.findall(r"\d+", " ".join(c.text for c in context)))
    return bool(nums - ctx)


def case_diagnostics(case: EvalCase, row: dict, chunks: dict[str, Chunk], k: int = 5) -> dict:
    """Métricas de un caso. `row` es una fila de `cases` del JSON de e2e."""
    out: dict = {"id": case.id, "category": case.category, "game": case.game}
    if row.get("error"):
        return out | {"error": True}
    ctx = [chunks[i] for i in row.get("context", []) if i in chunks]
    cited = [chunks[i] for i in row.get("sources", []) if i in chunks]
    abstained = bool(row.get("abstained"))
    out["abstained"], out["answerable"] = abstained, case.answerable
    if case.answerable and case.evidence and row.get("route", "documents") == "documents":
        rels = [bool(parts_found(case, c)) for c in ctx]
        covered = set().union(*(parts_found(case, c) for c in ctx)) if ctx else set()
        cited_covered = set().union(*(parts_found(case, c) for c in cited)) if cited else set()
        first = next((i for i, r in enumerate(rels, 1) if r), None)
        out |= {
            "recall": float(any(rels[:k])), "mrr": 1 / first if first else 0.0, "ndcg": ndcg_at_k(rels, k),
            "coverage": len(covered) / len(case.evidence),
            "noise": (1 - sum(rels) / len(rels)) if rels else None,
            "cite_recall": len(cited_covered) / len(case.evidence) if not abstained else None,
            "answered_without_evidence": (not abstained) and not any(rels),
        }
    if ctx:
        out["redundancy"] = redundancy(ctx)
    if not abstained and row.get("answer"):
        g, uns = groundedness(row["answer"], cited or ctx)
        out |= {"groundedness": g, "unsupported": uns, "novel_number": novel_number(row["answer"], ctx)}
    return out


def _avg(rows: list[dict], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if r.get(key) is not None]
    return round(mean(vals), 4) if vals else None


def aggregate(diags: list[dict]) -> dict:
    ok = [d for d in diags if not d.get("error")]
    unans = [d for d in ok if not d["answerable"]]
    ans = [d for d in ok if d["answerable"]]
    tp = sum(d["abstained"] for d in unans)  # abstención correcta
    fp = sum(d["abstained"] for d in ans)  # abstención innecesaria
    fn = sum(not d["abstained"] for d in unans)  # respondió lo que no debía
    prec = tp / (tp + fp) if unans and tp + fp else None  # sin no-respondibles la precision no esta definida
    rec = tp / (tp + fn) if tp + fn else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if prec is not None and rec is not None else None)
    answered = [d for d in ans if not d["abstained"] and "answered_without_evidence" in d]
    return {
        "n": len(diags), "n_retrieval_eval": sum("recall" in d for d in ok),
        "recall@5": _avg(ok, "recall"), "mrr": _avg(ok, "mrr"), "ndcg@5": _avg(ok, "ndcg"),
        "coverage": _avg(ok, "coverage"), "noise": _avg(ok, "noise"), "redundancy": _avg(ok, "redundancy"),
        "cite_recall": _avg(ok, "cite_recall"), "groundedness": _avg(ok, "groundedness"),
        "unsupported_rate": _avg(ok, "unsupported"), "novel_number_rate": _avg(ok, "novel_number"),
        "abstain_precision": round(prec, 4) if prec is not None else None,
        "abstain_recall": round(rec, 4) if rec is not None else None,
        "abstain_f1": round(f1, 4) if f1 is not None else None,
        "false_abstain_rate": round(fp / len(ans), 4) if ans else None,
        "overconfident_rate": round(fn / len(unans), 4) if unans else None,
        "answered_without_evidence": (round(mean(d["answered_without_evidence"] for d in answered), 4)
                                      if answered else None),
    }


def diagnose(result_cases: list[dict], cases: dict[str, EvalCase], chunks: dict[str, Chunk]) -> tuple[list[dict], dict]:
    diags = [case_diagnostics(cases[r["id"]], r, chunks) for r in result_cases if r["id"] in cases]
    return diags, aggregate(diags)
