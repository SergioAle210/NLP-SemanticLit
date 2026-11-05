"""Métricas de recuperación (definiciones del curso, tema 08 "Evaluación y diagnóstico").

Todas operan sobre una lista de juicios de relevancia ordenada por ranking: rels[0] es el top-1.

- Recall@k (hit rate): 1 si hay al menos un resultado relevante en el top-k.
  Promediado sobre consultas = "consultas con evidencia relevante en top-k / total de consultas".
- Precision@k: resultados relevantes en el top-k / k.
- Reciprocal rank: 1 / posición del primer relevante (0 si no aparece). Promedio = MRR.
- Coverage@k (propia): fracción de las partes de evidencia cubiertas en el top-k; distingue, en
  preguntas compuestas, si se recuperó toda la evidencia o solo una parte.
"""

from __future__ import annotations

from collections.abc import Sequence


def recall_at_k(rels: Sequence[bool], k: int) -> float:
    return 1.0 if any(rels[:k]) else 0.0


def precision_at_k(rels: Sequence[bool], k: int) -> float:
    if k <= 0:
        raise ValueError("k debe ser positivo")
    return sum(rels[:k]) / k


def reciprocal_rank(rels: Sequence[bool]) -> float:
    for pos, rel in enumerate(rels, 1):
        if rel:
            return 1.0 / pos
    return 0.0


def coverage_at_k(parts_per_hit: Sequence[set[int]], n_parts: int, k: int) -> float:
    if n_parts == 0:
        return 0.0
    covered = set().union(*parts_per_hit[:k]) if parts_per_hit[:k] else set()
    return len(covered) / n_parts


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0
