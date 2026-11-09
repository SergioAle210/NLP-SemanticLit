"""Planner de descomposición de consulta.

Divide una pregunta compuesta o multi-salto en 1–3 sub-preguntas autocontenidas, cada una para una búsqueda
independiente (la unión de los contextos cubre todas las partes). Las preguntas simples no se descomponen.
*Fail-open*: ante cualquier fallo del LLM devuelve la pregunta original (el flujo sigue como sin planner).
"""

from __future__ import annotations

import json
import logging

from gamerag.llm import LLMClient

log = logging.getLogger(__name__)

SYSTEM = (
    "You split a player's question about a NES game into independent search queries. If the question asks "
    "for two or more separate facts (different items, bosses, locations, or a fact plus a related "
    "requirement), return one self-contained query per fact (max 3), each naming its subject explicitly, "
    "keeping the game's proper nouns. If it asks for a single fact, return exactly one query equal to the "
    "question. Never invent names that are not implied by the question."
)

SCHEMA = {
    "type": "object",
    "properties": {"queries": {"type": "array", "items": {"type": "string"}}},
    "required": ["queries"],
    "additionalProperties": False,
}


class QueryPlanner:
    def __init__(self, llm: LLMClient | None = None, *, max_queries: int = 3, run: str = "serve"):
        self.llm = llm or LLMClient()
        self.max_queries, self.run = max_queries, run

    def plan(self, question: str) -> list[str]:
        try:
            msg = self.llm.complete(
                [{"role": "user", "content": question}], system=SYSTEM, max_tokens=200, run=self.run,
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            )
            queries = [q.strip() for q in json.loads(self.llm.text(msg))["queries"] if q.strip()]
        except Exception as exc:  # noqa: BLE001 - fail-open
            log.warning("planner falló (%s: %s); se usa la pregunta original", type(exc).__name__, exc)
            return [question]
        return queries[: self.max_queries] or [question]
