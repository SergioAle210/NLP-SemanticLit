"""Construye recuperadores por nombre: bm25 | dense | hybrid.

Punto único que usan la evaluación y la API, para que lo que se mide sea lo que se sirve.
"""

from __future__ import annotations

from typing import Literal

from gamerag.ingest.models import Chunk
from gamerag.retrieval.bm25 import BM25Index
from gamerag.retrieval.hybrid import HybridRetriever, Retriever
from gamerag.settings import Settings

RetrieverName = Literal["bm25", "dense", "hybrid"]


def make_retriever(name: RetrieverName, chunks: list[Chunk], settings: Settings,
                   model_key: str | None = None, reranker: str | None = None, expand: bool = False) -> Retriever:
    """Arma el recuperador por capas: base (bm25/dense/hybrid) -> [multi-consulta con el glosario del
    juego si `expand`] -> [reranker si se indica la clave de gamerag.retrieval.rerank.RERANKERS]."""
    base = _make_base(name, chunks, settings, model_key)
    if expand:
        from gamerag.games import load_all_games
        from gamerag.retrieval.query_expansion import ExpandingRetriever, QueryExpander

        cfg = load_all_games(settings.path(settings.games_config_dir))[chunks[0].game]
        base = ExpandingRetriever(base, QueryExpander(cfg.query_expansion, chunks))
    if reranker is None:
        return base
    from gamerag.retrieval.rerank import RerankingRetriever, get_reranker

    return RerankingRetriever(base, get_reranker(reranker, str(settings.path(settings.models_dir))))


def _make_base(name: RetrieverName, chunks: list[Chunk], settings: Settings, model_key: str | None) -> Retriever:
    if name == "bm25":
        return BM25Index(chunks)

    # Dependencias pesadas solo si se pide búsqueda semántica.
    from gamerag.retrieval.dense import DenseIndex
    from gamerag.retrieval.embeddings import get_embedder

    key = model_key or settings.embedding_model
    embedder = get_embedder(key, str(settings.path(settings.models_dir)))
    dense = DenseIndex(chunks, embedder, settings.path(settings.index_dir) / "chroma")
    if name == "dense":
        return dense
    if name == "hybrid":
        return HybridRetriever([BM25Index(chunks), dense])
    raise ValueError(f"recuperador desconocido: {name}")
