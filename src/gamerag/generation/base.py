"""Contrato de generación (ver docs/contracts/generation.md).

Un `Generator` recibe la pregunta y los chunks **ya filtrados** por los gates, y devuelve un `Answer`
(schemas.py) que cumple el §11 del curso. Implementaciones:

- `ExtractiveGenerator` (aquí): sin LLM. Devuelve los fragmentos más relevantes con sus citas.
  Es el generador por defecto mientras no haya API key, y el **respaldo** cuando el LLM falla.
- `FallbackGenerator` (aquí): envuelve un generador primario (p. ej. Haiku) y, si lanza una
  excepción, responde con el extractivo marcando `needs_human_review` (degradación controlada).
- `HaikuGenerator` (pendiente, otro integrante): Augmentation + Generation con Claude Haiku.
"""

from __future__ import annotations

import logging
from typing import Protocol

from gamerag.retrieval.bm25 import Hit
from gamerag.schemas import Answer, Source

log = logging.getLogger(__name__)

ABSTAIN_MESSAGE = "There is not enough information in the indexed sources to answer this question."


class Generator(Protocol):
    name: str

    def generate(self, question: str, context: list[Hit], *, game: str, trace_id: str) -> Answer:
        """`context` ya viene filtrado por los gates y ordenado por relevancia (rank 1 primero).
        Debe citar solo chunks de `context` y abstenerse si no hay evidencia suficiente."""
        ...


def to_source(hit: Hit) -> Source:
    return Source(source=hit.chunk.source, page=hit.chunk.page, chunk_id=hit.chunk.chunk_id)


def format_context(context: list[Hit]) -> str:
    """Formato estándar del contexto para un prompt (Augmentation).

    Cada chunk va delimitado y etiquetado con su chunk_id, para que el modelo pueda citarlo y para
    que el texto recuperado se trate como **datos, no como instrucciones** (mitigación de inyección).
    """
    blocks = []
    for h in context:
        c = h.chunk
        blocks.append(
            f'<document chunk_id="{c.chunk_id}" source="{c.source}" section="{c.section}">\n'
            f"{c.text}\n</document>"
        )
    return "\n\n".join(blocks)


class ExtractiveGenerator:
    """Respuesta sin LLM: los primeros `max_excerpts` fragmentos, recortados, con sus citas."""

    name = "extractive"

    def __init__(self, max_excerpts: int = 3, max_chars: int = 400):
        self.max_excerpts, self.max_chars = max_excerpts, max_chars

    def generate(self, question: str, context: list[Hit], *, game: str, trace_id: str) -> Answer:
        if not context:
            return Answer(answer=ABSTAIN_MESSAGE, abstained=True, game=game, trace_id=trace_id)
        used = context[: self.max_excerpts]
        lines = ["Most relevant excerpts from the sources (no generated summary):"]
        for i, h in enumerate(used, 1):
            body = " ".join(h.chunk.text.split())
            if len(body) > self.max_chars:
                body = body[: self.max_chars].rsplit(" ", 1)[0] + "…"
            lines.append(f"[{i}] {body}")
        return Answer(answer="\n".join(lines), sources=[to_source(h) for h in used],
                      abstained=False, game=game, trace_id=trace_id)


class FallbackGenerator:
    """Usa `primary`; si falla (API caída, timeout, respuesta inválida), responde con `fallback`
    y marca `needs_human_review=True`. Es la "degradación controlada" del banco de pruebas."""

    def __init__(self, primary: Generator, fallback: Generator | None = None):
        self.primary = primary
        self.fallback = fallback or ExtractiveGenerator()
        self.name = f"{primary.name}+fallback"
        self.last_error: str | None = None

    def generate(self, question: str, context: list[Hit], *, game: str, trace_id: str) -> Answer:
        try:
            self.last_error = None
            return self.primary.generate(question, context, game=game, trace_id=trace_id)
        except Exception as exc:  # noqa: BLE001 - cualquier falla del primario degrada al respaldo
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.warning("generador %s falló (%s); se usa %s", self.primary.name, self.last_error, self.fallback.name)
            answer = self.fallback.generate(question, context, game=game, trace_id=trace_id)
            return answer.model_copy(update={"needs_human_review": True})
