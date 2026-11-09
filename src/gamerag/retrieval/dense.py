"""Recuperación semántica con embeddings + ChromaDB embebido (fase 3).

- Un índice (colección de Chroma) por juego × chunker × modelo, persistido en data/index/.
- Huella (fingerprint) de los chunks y del modelo guardada en la colección: si cambian, se reconstruye.
- El score es la similitud coseno, calculada como producto punto de vectores normalizados
  (independiente de cómo cada versión de Chroma reporte la distancia).
- Los metadatos de ubicación se guardan en Chroma para que los gates puedan usar `where` (pre-filtro).

Requiere el extra `semantic`.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np

from gamerag.ingest.models import Chunk
from gamerag.retrieval.bm25 import INDEX_TEXT_VERSION, Hit, index_text
from gamerag.retrieval.embeddings import Embedder

_CLIENTS: dict[str, object] = {}


def _client(persist_dir: Path):
    """Un solo cliente de Chroma por directorio y proceso: abrir varios sobre la misma ruta deja los más
    antiguos con segmentos HNSW inválidos ("Nothing found on disk") en cuanto se abren/crean otras colecciones."""
    import chromadb

    key = str(persist_dir.resolve())
    if key not in _CLIENTS:
        _CLIENTS[key] = chromadb.PersistentClient(path=key)
    return _CLIENTS[key]


def _fingerprint(chunks: list[Chunk], model_key: str) -> str:
    h = hashlib.sha256(f"{model_key}|{INDEX_TEXT_VERSION}".encode())
    for c in chunks:
        h.update(c.chunk_id.encode() + c.hash.encode())
    return h.hexdigest()[:16]


def _collection_name(game: str, chunker: str, model_key: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "-", f"{game}__{chunker}__{model_key}")[:120]


def _metadata(c: Chunk) -> dict:
    meta = {"game": c.game, "source": c.source, "section": c.section}
    meta |= {k: v for k, v in c.location.model_dump().items() if v is not None}  # Chroma no admite None
    return meta


class DenseIndex:
    def __init__(self, chunks: list[Chunk], embedder: Embedder, persist_dir: Path):
        if not chunks:
            raise ValueError("no hay chunks para indexar")
        self.chunks = {c.chunk_id: c for c in chunks}
        self._all: tuple[list[str], np.ndarray] | None = None
        self.embedder = embedder
        self.model_key = embedder.model.key
        persist_dir.mkdir(parents=True, exist_ok=True)
        client = _client(persist_dir)
        name = _collection_name(chunks[0].game, chunks[0].chunker, self.model_key)
        fp = _fingerprint(chunks, self.model_key)

        existing = {col.name for col in client.list_collections()}
        if name in existing:
            col = client.get_collection(name)
            if (col.metadata or {}).get("fingerprint") == fp and col.count() == len(chunks):
                self._col, self.rebuilt = col, False
                return
            client.delete_collection(name)
        self._col = client.create_collection(name, metadata={"fingerprint": fp, "model": self.model_key})
        self._build(chunks)
        self.rebuilt = True

    def _build(self, chunks: list[Chunk]) -> None:
        # Mismo texto que BM25 (ruta de la página + chunk): ambos recuperadores ven lo mismo.
        vectors = self.embedder.embed_passages([index_text(c) for c in chunks])
        self._col.add(
            ids=[c.chunk_id for c in chunks],
            embeddings=vectors.tolist(),
            metadatas=[_metadata(c) for c in chunks],
        )

    def _vectors(self, where: dict | None) -> tuple[list[str], np.ndarray]:
        """Ids y vectores (filtrados por `where`). Se leen con `get`, que no pasa por el indice HNSW: como la busqueda
        es exacta no lo necesita, y asi no depende del segmento HNSW, que Chroma puede descartar y no recargar
        ("Nothing found on disk") cuando hay muchas colecciones abiertas en un mismo proceso."""
        if where is None and self._all is not None:
            return self._all
        res = self._col.get(where=where, include=["embeddings"])
        out = list(res["ids"]), np.asarray(res["embeddings"], dtype=np.float32).reshape(len(res["ids"]), -1)
        if where is None:
            self._all = out
        return out

    def search(self, query: str, k: int = 5, where: dict | None = None) -> list[Hit]:
        """Búsqueda **exacta**: se piden a Chroma todos los chunks (que cumplan `where`) y se ordenan
        por coseno exacto. HNSW es aproximado: con n_results = k, a veces omitía un vecino del top-k,
        y de forma no determinista entre procesos (1 de 3 corridas; una evaluación dio Recall@5 0.89
        en vez de 0.92). Con ~250 chunks por juego, comparar contra todos cuesta milisegundos. Con
        un corpus grande habría que volver a n_results = k y subir `ef_search`."""
        q = self.embedder.embed_query(query)
        ids, embs = self._vectors(where)
        sims = embs @ q if len(ids) else np.array([])
        # Orden por similitud coseno exacta; en empate, por chunk_id para que sea determinista.
        order = sorted(range(len(ids)), key=lambda i: (-sims[i], ids[i]))[:k]
        return [Hit(rank=r, score=float(sims[i]), chunk=self.chunks[ids[i]]) for r, i in enumerate(order, 1)]
