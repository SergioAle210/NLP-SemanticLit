"""Esquema y carga del banco de pruebas (`eval/cases.jsonl`).

La relevancia se define por **evidencia textual**, no por chunk_id: un chunk es relevante para un
caso si proviene de una de las `expected_sources` y contiene alguna alternativa de alguna parte de
`evidence`. Así el mismo banco sirve para comparar estrategias de chunking distintas.

`evidence` es una lista de partes; cada parte, una lista de alternativas equivalentes:
    [["Blue Candle 60 R", "Blue Candle for 60 rupees"], ["burn bushes in the overworld"]]
Una pregunta compuesta tiene varias partes; una simple, una sola.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from gamerag.ingest.models import Chunk

Category = Literal[
    "direct", "paraphrase", "exact_id", "compound", "ambiguous", "unanswerable", "version",
    "multigame", "tool", "security",
]


class EvalCase(BaseModel):
    # --- campos obligatorios del curso (§8) ---
    id: str
    question: str
    expected_behavior: str
    expected_sources: list[str]
    expected_pages: list[int] = Field(description="Índice de sección por cada fuente esperada (mismo orden)")
    answerable: bool
    risk_level: Literal["low", "medium", "high", "critical"]
    # --- propios ---
    category: Category
    game: str
    profile: str
    lang: str = "en"
    evidence: list[list[str]] = []

    @model_validator(mode="after")
    def _consistent(self) -> EvalCase:
        if len(self.expected_pages) != len(self.expected_sources):
            raise ValueError(f"{self.id}: expected_pages debe alinearse con expected_sources")
        if self.answerable and not self.evidence:
            raise ValueError(f"{self.id}: un caso con respuesta necesita evidence")
        if not self.answerable and (self.evidence or self.expected_sources):
            raise ValueError(f"{self.id}: un caso sin respuesta no lleva evidencia ni fuentes")
        return self


def load_cases(path: Path) -> list[EvalCase]:
    with path.open(encoding="utf-8") as f:
        cases = [EvalCase.model_validate(json.loads(line)) for line in f if line.strip()]
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("ids de casos duplicados")
    return cases


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def parts_found(case: EvalCase, chunk: Chunk) -> set[int]:
    """Índices de las partes de evidencia que contiene el chunk (vacío si no es de una fuente esperada)."""
    if chunk.source not in case.expected_sources:
        return set()
    text = _norm(chunk.text)
    return {i for i, alts in enumerate(case.evidence) if any(_norm(a) in text for a in alts)}


def is_relevant(case: EvalCase, chunk: Chunk) -> bool:
    return bool(parts_found(case, chunk))
