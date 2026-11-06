"""Contratos de control de acceso y guardrails (ver docs/contracts/access-and-guardrails.md).

Tres puntos de enganche en el pipeline:

    pregunta ─► InputGuard ─► recuperación ─► AccessFilter ─► Generator ─► OutputGuard ─► respuesta

- `InputGuard.check(question, profile)`: valida la pregunta antes de buscar (longitud, inyección, PII).
- `AccessFilter.allows(chunk, profile)`: decide si un chunk puede llegar al LLM (gates G1-G4).
- `OutputGuard.check(answer, context, profile)`: valida la respuesta antes de devolverla
  (citas dentro del contexto, entidades bloqueadas, juego correcto).

Las implementaciones de aquí son las **por defecto**: mínimas y funcionales. Los gates de spoilers
(G2, G2b, G3, G4) y los detectores de inyección/PII se implementan respetando estas interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from gamerag.ingest.models import Chunk
from gamerag.progress.models import Profile
from gamerag.retrieval.bm25 import Hit
from gamerag.schemas import Answer


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: str = ""  # por qué se bloqueó (queda en la traza de auditoría)
    flags: list[str] = field(default_factory=list)  # señales no bloqueantes (p. ej. "pii_redacted")


class InputGuard(Protocol):
    name: str

    def check(self, question: str, profile: Profile) -> GuardResult: ...


class AccessFilter(Protocol):
    name: str

    def allows(self, chunk: Chunk, profile: Profile, game: str) -> bool:
        """True si el chunk puede usarse como evidencia para este perfil en este juego."""
        ...


class OutputGuard(Protocol):
    name: str

    def check(self, answer: Answer, context: list[Hit], profile: Profile) -> GuardResult: ...


# --- implementaciones por defecto -----------------------------------------------------------

class BasicInputGuard:
    """Validación estructural mínima (§5.8 "validación de entradas"). La detección de inyección y PII
    se agrega en otro InputGuard encadenado."""

    name = "basic_input"

    def __init__(self, max_chars: int = 500):
        self.max_chars = max_chars

    def check(self, question: str, profile: Profile) -> GuardResult:
        q = question.strip()
        if not q:
            return GuardResult(False, "empty_question")
        if len(q) > self.max_chars:
            return GuardResult(False, f"question_too_long(>{self.max_chars})")
        return GuardResult(True)


class GameFilter:
    """Gate G1: solo chunks del juego activo. Implementado como ejemplo del patrón AccessFilter."""

    name = "g1_game"

    def allows(self, chunk: Chunk, profile: Profile, game: str) -> bool:
        return chunk.game == game


class CitationGuard:
    """Las citas deben pertenecer al contexto entregado y la respuesta al juego activo (§11)."""

    name = "citations"

    def check(self, answer: Answer, context: list[Hit], profile: Profile) -> GuardResult:
        allowed_ids = {h.chunk.chunk_id for h in context}
        foreign = [s.chunk_id for s in answer.sources if s.chunk_id not in allowed_ids]
        if foreign:
            return GuardResult(False, f"citations_outside_context:{foreign}")
        if context and answer.game != context[0].chunk.game:
            return GuardResult(False, "answer_game_mismatch")
        return GuardResult(True)
