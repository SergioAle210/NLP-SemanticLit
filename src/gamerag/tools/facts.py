"""Herramienta `query_game_facts`: datos estructurados del juego en SQLite (solo lectura).

Por qué una herramienta y no solo RAG: las preguntas de lista o tabla ("list all the bosses in the
first quest") necesitan datos repartidos en varios chunks; con top-5 el RAG devuelve solo una parte
(docs/evaluation/results.md, "Cobertura"). La tabla se extrae de la página Bosses de la wiki en la
carga, y cada fila conserva el chunk de origen para citarlo.

Controles (§5.8, límites de alcance): consultas **parametrizadas** predefinidas (no hay SQL libre),
conexión de solo lectura, parámetros validados contra la configuración del juego y límite de filas.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from gamerag.games import GameConfig
from gamerag.ingest.models import Chunk

MAX_ROWS = 50
_ROW = re.compile(r"^Name: (?P<name>[^|]+?) \| HP: (?P<hp>[^|]+?) \| Damage: (?P<dmg>[^|]+?) \| "
                  r"Description: (?P<desc>.*)$", re.M)
_QUEST = {"first": re.compile(r"1st Quest: ([^;]*)"), "second": re.compile(r"2nd Quest: ([^;]*)")}
_APPEARANCE = re.compile(r"(\d+)\s*(\(Boss\))?")


class ToolParamError(ValueError):
    """Parámetros fuera de rango o inválidos: la herramienta no se ejecuta."""


@dataclass(frozen=True)
class BossRow:
    name: str
    hp: str
    damage: str
    quest: str
    level: int
    chunk_id: str


def parse_boss_rows(chunk: Chunk) -> list[BossRow]:
    """Filas `Name: X | HP | Damage | Description: 1st Quest: 1 (Boss), 7.; 2nd Quest: ...` de la
    página Bosses -> una fila por (jefe, quest, nivel) donde es **jefe** de la mazmorra."""
    rows = []
    for m in _ROW.finditer(chunk.text):
        for quest, pattern in _QUEST.items():
            seg = pattern.search(m["desc"])
            if not seg:
                continue
            for level, is_boss in _APPEARANCE.findall(seg.group(1)):
                if is_boss:
                    rows.append(BossRow(m["name"].strip(), m["hp"].strip(), m["dmg"].strip(), quest,
                                        int(level), chunk.chunk_id))
    return rows


class GameFacts:
    """Tabla `bosses` en SQLite en memoria, construida desde los chunks del juego."""

    name = "query_game_facts"

    def __init__(self, config: GameConfig, chunks: list[Chunk]):
        self.config = config
        self.chunks = {c.chunk_id: c for c in chunks}
        rows = [r for c in chunks if c.source.endswith("/Bosses") for r in parse_boss_rows(c)]
        self._db = sqlite3.connect(":memory:", check_same_thread=False)
        self._db.execute("CREATE TABLE bosses (name TEXT, hp TEXT, damage TEXT, quest TEXT, level INTEGER, "
                         "chunk_id TEXT)")
        self._db.executemany("INSERT INTO bosses VALUES (?, ?, ?, ?, ?, ?)",
                             [(r.name, r.hp, r.damage, r.quest, r.level, r.chunk_id) for r in rows])
        self._db.execute("PRAGMA query_only = ON")  # a partir de aquí, solo lectura
        self.n_rows = len(rows)

    @property
    def available(self) -> bool:
        return self.n_rows > 0

    def validate(self, quest: str | None, level: int | None) -> None:
        if quest is not None and quest not in (self.config.quests or []):
            raise ToolParamError(f"quest '{quest}' does not exist (valid: {', '.join(self.config.quests or [])})")
        if level is not None and level not in (self.config.levels or []):
            lv = self.config.levels or []
            raise ToolParamError(f"level {level} does not exist in {self.config.title} "
                                 f"(valid: {min(lv)}-{max(lv)})" if lv else f"level {level} does not exist")

    def bosses(self, quest: str | None = None, level: int | None = None) -> list[BossRow]:
        """Jefes de mazmorra, filtrados por quest y nivel (consulta parametrizada)."""
        self.validate(quest, level)
        sql = "SELECT name, hp, damage, quest, level, chunk_id FROM bosses WHERE 1=1"
        args: list = []
        if quest is not None:
            sql += " AND quest = ?"
            args.append(quest)
        if level is not None:
            sql += " AND level = ?"
            args.append(level)
        sql += " ORDER BY quest, level, name LIMIT ?"
        args.append(MAX_ROWS)
        return [BossRow(*r) for r in self._db.execute(sql, args).fetchall()]
