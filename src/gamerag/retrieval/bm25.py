"""Recuperación léxica con BM25 (línea base, fase 2).

Se indexa el título de la página **sin el nombre del juego** + el texto del chunk:
- El título aporta términos de ubicación ("Underworld", "Quest 1", "Dungeon 4") que no siempre
  aparecen en el texto. Sin él fallan las preguntas de versión (Q1 vs Q2).
- El nombre del juego ("The Legend of Zelda/...") se quita: estaría en todos los chunks, así que no
  discrimina y le quita peso a esas palabras cuando sí importan (p. ej. "register my name as ZELDA").
Ablación en docs/retrieval/bm25.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from gamerag.ingest.models import Chunk
from gamerag.retrieval.tokenize import tokenize


@dataclass(frozen=True)
class Hit:
    rank: int  # 1 = primer resultado
    score: float
    chunk: Chunk


def load_chunks(path: Path) -> list[Chunk]:
    with path.open(encoding="utf-8") as f:
        return [Chunk.model_validate(json.loads(line)) for line in f if line.strip()]


# Cambiar si cambia `index_text`: forma parte de la huella de los índices persistidos (Chroma),
# para que un cambio en lo que se indexa obligue a reconstruirlos.
INDEX_TEXT_VERSION = "path+text/v1"


def index_text(chunk: Chunk) -> str:
    """Texto que se indexa (léxico **y** semántico): ruta de la página sin el nombre del juego + texto."""
    _, _, path_in_game = chunk.source.partition("/")  # "The Legend of Zelda/Items" -> "Items"
    return f"{path_in_game}\n{chunk.text}"


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        if not chunks:
            raise ValueError("no hay chunks para indexar")
        self.chunks = chunks
        self.k1, self.b = k1, b
        self._bm25 = BM25Okapi([tokenize(index_text(c)) for c in chunks], k1=k1, b=b)

    def search(self, query: str, k: int = 5) -> list[Hit]:
        terms = tokenize(query)
        if not terms:
            return []
        scores = self._bm25.get_scores(terms)
        # Solo chunks con score > 0: un chunk sin ningún término de la consulta no es un candidato
        # léxico. Sin este filtro, BM25 rellenaba el top-k con chunks de score 0 en orden de corpus,
        # y RRF los premiaba por aparecer en la lista (bug detectado en la prueba de punta a punta).
        matching = [i for i in range(len(scores)) if scores[i] > 0]
        # Orden estable: score descendente y, en empate, el orden original del corpus.
        order = sorted(matching, key=lambda i: (-scores[i], i))[:k]
        return [Hit(rank=r, score=float(scores[i]), chunk=self.chunks[i]) for r, i in enumerate(order, 1)]
