"""Contrato de salida del sistema (§11 de las instrucciones del proyecto).

Toda respuesta que sale de la API se valida contra `Answer`. Los campos obligatorios del curso son
answer, sources, abstained, tool_used y needs_human_review; el resto son extensiones propias.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Source(BaseModel):
    source: str = Field(min_length=1, description="Documento de origen (página de la wiki o PDF)")
    page: int = Field(ge=0, description="Página del PDF o índice de sección en la wiki")
    chunk_id: str = Field(min_length=1)


class Answer(BaseModel):
    answer: str
    sources: list[Source] = []
    abstained: bool
    tool_used: str | None = None
    needs_human_review: bool = False

    # --- extensiones propias ---
    game: str = Field(description="Juego al que pertenece la respuesta (verificación de aislamiento)")
    blocked_by_spoiler: bool = False
    trace_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _grounded_or_abstained(self) -> Answer:
        # Generación fundamentada: una respuesta afirmativa sin citas no es aceptable
        # (salvo que provenga de una herramienta determinista, p. ej. SQL o el grafo).
        if not self.abstained and not self.blocked_by_spoiler and not self.sources and not self.tool_used:
            raise ValueError("respuesta sin abstención debe tener fuentes o provenir de una herramienta")
        return self
