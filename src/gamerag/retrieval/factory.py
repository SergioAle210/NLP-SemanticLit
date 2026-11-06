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
                   model_key: str | None = None) -> Retriever:
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
