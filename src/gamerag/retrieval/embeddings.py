"""Modelos de embeddings para la búsqueda semántica (fase 3).

Cada modelo tiene sus propias convenciones de prefijos: usar las de otro modelo degrada la calidad
**sin error visible**, por eso viven en un registro explícito (ver docs/retrieval/semantic.md).

Requiere el extra `semantic` (`uv sync --extra semantic`): torch, sentence-transformers.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np


@dataclass(frozen=True)
class EmbeddingModel:
    key: str
    hf_name: str
    query_prefix: str = ""
    passage_prefix: str = ""
    multilingual: bool = False


MODELS: dict[str, EmbeddingModel] = {
    # Inglés. Para v1.5 el prefijo de consulta es opcional según la ficha del modelo; se usa el recomendado.
    "bge-small-en": EmbeddingModel(
        "bge-small-en", "BAAI/bge-small-en-v1.5",
        query_prefix="Represent this sentence for searching relevant passages: ",
    ),
    # Multilingüe. E5 exige "query: " y "passage: " (entrenado así).
    "e5-small-multi": EmbeddingModel(
        "e5-small-multi", "intfloat/multilingual-e5-small",
        query_prefix="query: ", passage_prefix="passage: ", multilingual=True,
    ),
}


class Embedder:
    """Codifica textos en vectores normalizados (norma 1): similitud coseno = producto punto."""

    def __init__(self, model: EmbeddingModel, cache_folder: str | None = None, device: str = "cpu"):
        from sentence_transformers import SentenceTransformer  # import diferido: dependencia opcional

        self.model = model
        self._st = SentenceTransformer(model.hf_name, cache_folder=cache_folder, device=device)

    @property
    def dim(self) -> int:
        return int(self._st.get_sentence_embedding_dimension())

    def embed_passages(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        return self._encode([self.model.passage_prefix + t for t in texts], batch_size)

    def embed_query(self, text: str) -> np.ndarray:
        return self._encode([self.model.query_prefix + text], 1)[0]

    def _encode(self, texts: list[str], batch_size: int) -> np.ndarray:
        return self._st.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                               convert_to_numpy=True, show_progress_bar=False)


@lru_cache(maxsize=4)
def get_embedder(key: str, cache_folder: str | None = None) -> Embedder:
    """Carga cada modelo una sola vez por proceso (cargarlo toma decenas de segundos)."""
    if key not in MODELS:
        raise ValueError(f"modelo desconocido: {key}. Opciones: {', '.join(MODELS)}")
    return Embedder(MODELS[key], cache_folder=cache_folder)
