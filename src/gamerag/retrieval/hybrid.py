"""Búsqueda híbrida: fusión de rankings con Reciprocal Rank Fusion (RRF).

RRF combina **posiciones**, no scores: BM25 (p. ej. 7.12) y similitud coseno (0-1) están en escalas
distintas y no se pueden sumar directamente (curso, tema 08, diapositiva 198).

    rrf(d) = Σ_rankings 1 / (k + posición_de_d_en_el_ranking)

Con k = 60 (valor del artículo original de RRF, Cormack et al., 2009), un documento que aparece
bien posicionado en ambos rankings supera a uno que solo es primero en uno.

Este módulo no depende de torch: se puede usar y testear sin el extra `semantic`.
"""

from __future__ import annotations

from typing import Protocol

from gamerag.retrieval.bm25 import Hit

RRF_K = 60


class Retriever(Protocol):
    def search(self, query: str, k: int = 5) -> list[Hit]: ...


def rrf_fuse(rankings: list[list[Hit]], k: int = RRF_K, top_n: int | None = None) -> list[Hit]:
    scores: dict[str, float] = {}
    chunks = {}
    first_seen: dict[str, int] = {}
    for ranking in rankings:
        for hit in ranking:
            cid = hit.chunk.chunk_id
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + hit.rank)
            chunks[cid] = hit.chunk
            first_seen.setdefault(cid, len(first_seen))
    # Empate: el que apareció primero (en el orden de los rankings) va antes -> determinista.
    order = sorted(scores, key=lambda cid: (-scores[cid], first_seen[cid]))[:top_n]
    return [Hit(rank=r, score=scores[cid], chunk=chunks[cid]) for r, cid in enumerate(order, 1)]


class HybridRetriever:
    """Recupera `candidates` de cada recuperador y los fusiona con RRF.

    La profundidad de cada ranking (`candidates`) es **fija** e independiente del `k` pedido: RRF con
    listas más largas suma puntos a chunks que solo aparecen abajo y cambia el orden de los primeros.
    Antes se usaba max(k, candidates); el pipeline pedía k=50 y obtenía Recall@5 = 0.83 en vez del
    0.89 evaluado con profundidad 20 (docs/evaluation/results.md). Si k > candidates, se devuelven
    como máximo los chunks únicos de la unión de los rankings.
    """

    def __init__(self, retrievers: list[Retriever], candidates: int = 20, rrf_k: int = RRF_K):
        if not retrievers:
            raise ValueError("se necesita al menos un recuperador")
        self.retrievers, self.candidates, self.rrf_k = retrievers, candidates, rrf_k

    def search(self, query: str, k: int = 5) -> list[Hit]:
        return rrf_fuse([r.search(query, k=self.candidates) for r in self.retrievers], k=self.rrf_k, top_n=k)
