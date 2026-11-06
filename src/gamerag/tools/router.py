"""Router de intención (flujo de decisión, §5.6 opción 2) y ejecución de herramientas.

    pregunta -> Router -> documents         -> RAG (recuperación + generación)
                       -> query_game_facts  -> SQL de solo lectura (tabla de jefes)
                       -> next_available_levels -> progreso del perfil (sin spoilers)
                       -> update_progress   -> NO se ejecuta: requiere confirmación humana

Reglas explícitas y auditables (sin LLM): cada decisión queda en la traza con su motivo. Ante la duda,
el router elige `documents` (el RAG es el comportamiento por defecto y nunca empeora por el router).
Solo se habilitan las herramientas listadas en `tools` de la configuración del juego.
Ver docs/tools/README.md.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from gamerag.games import GameConfig
from gamerag.ingest.models import Chunk, Location
from gamerag.progress.models import LevelSetProgress, Profile
from gamerag.retrieval.bm25 import Hit
from gamerag.tools.facts import GameFacts

DOCUMENTS = "documents"

_HOW = re.compile(r"\bhow\b", re.I)
_BOSS = re.compile(r"\bboss(es)?\b", re.I)
_LISTISH = re.compile(r"\b(who|which|what|list|all|every|name)\b", re.I)
_PROGRESS = re.compile(
    r"\b(what (should|do|can) i do next|what('s| is) next|where (should|do) i go next|"
    r"which (levels?|dungeons?|stages?) (can|should|do) i|next (level|dungeon|stage)|my progress)\b", re.I)
_UPDATE = re.compile(r"\bi (just |already )?(beat|finished|completed|cleared|passed)\b.*"
                     r"\b(level|dungeon|stage|act)\b", re.I)
_LEVEL = re.compile(r"\b(?:level|dungeon)[- ]?(\d+)\b", re.I)
_QUEST = [(re.compile(r"\b(first|1st) quest\b|\bquest[- ]?1\b", re.I), "first"),
          (re.compile(r"\b(second|2nd) quest\b|\bquest[- ]?2\b", re.I), "second")]


@dataclass
class Route:
    intent: str  # documents | query_game_facts | next_available_levels | update_progress
    reason: str
    params: dict = field(default_factory=dict)

    @property
    def is_tool(self) -> bool:
        return self.intent != DOCUMENTS


@dataclass
class ToolResult:
    answer: str
    hits: list[Hit] = field(default_factory=list)  # chunks citados (fuente de cada fila)
    abstained: bool = False
    needs_human_review: bool = False
    info: dict = field(default_factory=dict)  # filas devueltas, filas bloqueadas, etc. (traza)


# Devuelve el nombre del filtro que bloquea el chunk, o None si se permite.
Blocker = Callable[[Chunk], str | None]


class Router:
    def __init__(self, games: dict[str, GameConfig], facts: dict[str, GameFacts]):
        self.games = games
        self.facts = {g: f for g, f in facts.items() if f.available}

    def _enabled(self, game: str, tool: str) -> bool:
        return tool in (self.games[game].tools or [])

    def route(self, question: str, game: str) -> Route:
        q = question.strip()
        if _UPDATE.search(q) and self._enabled(game, "update_progress"):
            return Route("update_progress", "reports progress (action: requires confirmation)")
        if _PROGRESS.search(q) and self._enabled(game, "next_available_levels"):
            return Route("next_available_levels", "asks about the player's own progress")
        if (_BOSS.search(q) and _LISTISH.search(q) and not _HOW.search(q)
                and game in self.facts and self._enabled(game, "query_game_facts")):
            level = _LEVEL.search(q)
            quest = next((name for pattern, name in _QUEST if pattern.search(q)), None)
            return Route("query_game_facts", "list/lookup of bosses (structured table)",
                         {"table": "bosses", "quest": quest, "level": int(level.group(1)) if level else None})
        return Route(DOCUMENTS, "default: document retrieval")

    # --- ejecución -----------------------------------------------------------------------------

    def run(self, route: Route, game: str, profile: Profile, blocker: Blocker) -> ToolResult:
        if route.intent == "query_game_facts":
            return self._facts(route, game, profile, blocker)
        if route.intent == "next_available_levels":
            return _next_available(self.games[game], profile)
        if route.intent == "update_progress":
            return ToolResult(
                answer=("Updating your progress changes what you are allowed to see. It is not done "
                        "automatically: confirm it from your profile (an administrator can reset profiles)."),
                needs_human_review=True, info={"executed": False, "reason": "requires_confirmation"})
        raise ValueError(f"no es una herramienta: {route.intent}")

    def _facts(self, route: Route, game: str, profile: Profile, blocker: Blocker) -> ToolResult:
        facts = self.facts[game]
        quest, level = route.params.get("quest"), route.params.get("level")
        prog = profile.progress.get(game)
        if quest is None and not profile.unrestricted and isinstance(prog, LevelSetProgress):
            quest = prog.quest  # sin quest explícita: la del jugador
            route.params["quest"] = quest
        rows = facts.bosses(quest=quest, level=level)  # valida parámetros (ToolParamError)
        visible, blocked = [], 0
        for r in rows:
            # Cada fila se evalúa como si fuera un chunk ubicado en su (quest, nivel): los mismos gates
            # de spoilers del RAG se aplican a la herramienta.
            src = facts.chunks[r.chunk_id]
            located = src.model_copy(update={"location": Location(quest=r.quest, level=r.level)})
            if blocker(located) is None:
                visible.append(r)
            else:
                blocked += 1
        info = {"rows": len(visible), "blocked_rows": blocked}
        if not visible:
            msg = ("That information belongs to content you have not unlocked yet." if blocked
                   else "No bosses match that query.")
            return ToolResult(answer=msg, abstained=True, info=info)
        lines = [f"- {r.quest.title()} quest, level {r.level}: {r.name} (HP {r.hp}, damage {r.damage})"
                 for r in visible]
        if blocked:
            lines.append(f"({blocked} more hidden: content you have not unlocked yet.)")
        cited = list(dict.fromkeys(r.chunk_id for r in visible))
        hits = [Hit(rank=i, score=1.0, chunk=facts.chunks[cid]) for i, cid in enumerate(cited, 1)]
        return ToolResult(answer="Dungeon bosses:\n" + "\n".join(lines), hits=hits, info=info)


def _next_available(config: GameConfig, profile: Profile) -> ToolResult:
    """Qué puede jugar ahora, solo con números de nivel (no revela contenido). Solo para juegos no
    lineales (level_set): en uno lineal la siguiente etapa es trivial (validado en games.py)."""
    prog = profile.progress.get(config.game_id)
    if prog is None:
        return ToolResult(answer=f"There is no saved progress for {config.title}. Start with level "
                                 f"{(config.levels or ['?'])[0]}.", info={"progress": None})
    if isinstance(prog, LevelSetProgress):
        pending = [lv for lv in (config.levels or []) if lv not in prog.completed_levels]
        done = ", ".join(map(str, prog.completed_levels)) or "none"
        cur = f" You are currently on level {prog.current_level}." if prog.current_level else ""
        return ToolResult(answer=(f"{prog.quest.title()} quest. Completed levels: {done}.{cur} "
                                  f"Levels not completed yet: {', '.join(map(str, pending)) or 'none'}. "
                                  "In this game the dungeons can be done in any order, though higher "
                                  "numbers are usually harder."),
                          info={"pending": pending})
    return ToolResult(answer="This game does not track levels as a set.", abstained=True)
