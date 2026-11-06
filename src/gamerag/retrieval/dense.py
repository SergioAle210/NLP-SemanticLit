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
from gamerag.retrieval.bm25 import Hit
from gamerag.retrieval.embeddings import Embedder


def _fingerprint(chunks: list[Chunk], model_key: str) -> str:
    h = hashlib.sha256(model_key.encode())
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
        import chromadb  # import diferido: dependencia opcional

        if not chunks:
            raise ValueError("no hay chunks para indexar")
        self.chunks = {c.chunk_id: c for c in chunks}
        self.embedder = embedder
        self.model_key = embedder.model.key
        persist_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(persist_dir))
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
        vectors = self.embedder.embed_passages([c.text for c in chunks])
        self._col.add(
            ids=[c.chunk_id for c in chunks],
            embeddings=vectors.tolist(),
            metadatas=[_metadata(c) for c in chunks],
        )

    def search(self, query: str, k: int = 5, where: dict | None = None) -> list[Hit]:
        q = self.embedder.embed_query(query)
        res = self._col.query(query_embeddings=[q.tolist()], n_results=min(k, len(self.chunks)),
                              where=where, include=["embeddings"])
        ids, embs = res["ids"][0], np.asarray(res["embeddings"][0])
        sims = embs @ q if len(ids) else np.array([])
        # Orden por similitud coseno exacta; en empate, por chunk_id para que sea determinista.
        order = sorted(range(len(ids)), key=lambda i: (-sims[i], ids[i]))
        return [Hit(rank=r, score=float(sims[i]), chunk=self.chunks[ids[i]]) for r, i in enumerate(order, 1)]
