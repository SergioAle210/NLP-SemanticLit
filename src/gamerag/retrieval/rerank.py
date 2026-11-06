"""Reranking con cross-encoder: segunda etapa de la recuperación (curso, tema 08, "dos etapas").

Un bi-encoder (embeddings) codifica pregunta y chunk **por separado** y compara vectores: rápido, pero
no ve la interacción entre ambos textos. Un cross-encoder lee **pregunta y chunk juntos** y devuelve
un score de relevancia: más preciso y más lento. Por eso se aplica solo a los `candidates` mejores
de la primera etapa (híbrida).

Además, su score es una medida de relevancia de la pareja (pregunta, chunk), a diferencia del de
RRF (que solo refleja posiciones): sirve como base para un umbral de abstención.

Requiere el extra `semantic`. Ver docs/retrieval/rerank.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from gamerag.retrieval.bm25 import Hit, index_text
from gamerag.retrieval.hybrid import Retriever


@dataclass(frozen=True)
class RerankerModel:
    key: str
    hf_name: str
    multilingual: bool = False


RERANKERS: dict[str, RerankerModel] = {
    # Inglés, entrenado en MS MARCO (búsqueda de pasajes). ~22M parámetros.
    "minilm-en": RerankerModel("minilm-en", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
    # Multilingüe (mMARCO). ~118M parámetros. Mantiene abierta la fase 3d (español).
    "mminilm-multi": RerankerModel("mminilm-multi", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1", multilingual=True),
}


class CrossEncoderReranker:
    def __init__(self, model: RerankerModel, cache_folder: str | None = None, device: str = "cpu"):
        from sentence_transformers import CrossEncoder  # import diferido: dependencia opcional

        self.model = model
        self._ce = CrossEncoder(model.hf_name, cache_folder=cache_folder, device=device, max_length=512)

    def score(self, query: str, hits: list[Hit]) -> list[float]:
        if not hits:
            return []
        pairs = [(query, index_text(h.chunk)) for h in hits]
        return [float(s) for s in self._ce.predict(pairs, show_progress_bar=False)]


@lru_cache(maxsize=4)
def get_reranker(key: str, cache_folder: str | None = None) -> CrossEncoderReranker:
    if key not in RERANKERS:
        raise ValueError(f"reranker desconocido: {key}. Opciones: {', '.join(RERANKERS)}")
    return CrossEncoderReranker(RERANKERS[key], cache_folder=cache_folder)


class RerankingRetriever:
    """Primera etapa: `base` recupera `candidates` chunks. Segunda: el cross-encoder los reordena.

    La cantidad que se reordena es fija (`candidates`), independiente del k pedido, por la misma
    razón que en la híbrida: lo servido debe ser lo evaluado. Devuelve como máximo `candidates` hits,
    con `score` = score del cross-encoder (logit: mayor es más relevante; puede ser negativo).
    """

    def __init__(self, base: Retriever, reranker: CrossEncoderReranker, candidates: int = 20):
        self.base, self.reranker, self.candidates = base, reranker, candidates
        self.retrievers = getattr(base, "retrievers", [base])  # acceso a los recuperadores internos

    def search(self, query: str, k: int = 5) -> list[Hit]:
        first = self.base.search(query, k=self.candidates)
        scores = self.reranker.score(query, first)
        # Empate: se conserva el orden de la primera etapa.
        order = sorted(range(len(first)), key=lambda i: (-scores[i], i))[:k]
        return [Hit(rank=r, score=scores[i], chunk=first[i].chunk) for r, i in enumerate(order, 1)]
