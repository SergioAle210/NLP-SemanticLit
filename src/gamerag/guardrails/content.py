"""Proyección de evidencia antes de generar: secciones, filas y pasajes autorizados.

Las citas siguen identificando la misma fuente; ``source_hash`` conserva el hash
original y ``hash`` describe exactamente el texto entregado. Las reglas son
curadas por juego, no un clasificador semántico universal de spoilers.
"""

from __future__ import annotations

import hashlib
import re

from gamerag.games import ContentRule, GameConfig, LevelListRule
from gamerag.guardrails.location import LocationGate
from gamerag.ingest.location import locate
from gamerag.ingest.models import Chunk, Location
from gamerag.ingest.sections import Section
from gamerag.progress.models import LevelSetProgress, LinearStageProgress, Profile
from gamerag.tools.facts import BossRow, parse_boss_rows

_HEADING = re.compile(r"^\[([^\n]+)\]$")
_EXPLICIT_LEVEL = re.compile(r"^- Level (\d+): (.+)$")
_MAP_CELL = re.compile(r"^([A-Z]-[1-9]\d*):\s*", re.I)
_ENGLISH_NUMBERS = {
    word: number for number, words in enumerate((
        ("one", "first"), ("two", "second"), ("three", "third"), ("four", "fourth"),
        ("five", "fifth"), ("six", "sixth"), ("seven", "seventh"), ("eight", "eighth"),
        ("nine", "ninth"), ("ten", "tenth")), 1) for word in words
}
_NUMBER = r"(?:\d+(?:st|nd|rd|th)?|" + "|".join(_ENGLISH_NUMBERS) + r"|final|last)"
_JOIN = r"(?:,\s*(?:(?:and|or)\s+)?|(?:and|or|to|through)\s+|[-–]\s*)"
_NUMBER_LIST = _NUMBER + r"(?:\s*" + _JOIN + _NUMBER + r")*"
_LEVEL_REFERENCES = (
    re.compile(r"\b(?:levels?|dungeons?)\s*[-:#]?\s*(" + _NUMBER_LIST + r")\b", re.I),
    re.compile(r"\b(" + _NUMBER_LIST + r")\s+(?:levels?|dungeons?)\b", re.I),
)
_NUMBER_TOKEN = re.compile(r"\b" + _NUMBER + r"\b", re.I)
_NUMBER_RANGE = re.compile(r"\b(" + _NUMBER + r")\s*(?:[-–]|to|through)\s*(" + _NUMBER + r")\b", re.I)


def _referenced_levels(text: str, final_level: int) -> set[int]:
    """Niveles explícitos; '5 Heart Containers' y 'Section 5' no coinciden."""
    def number(token: str) -> int:
        token = token.lower()
        if token in ("last", "final"):
            return final_level
        return _ENGLISH_NUMBERS[token] if token in _ENGLISH_NUMBERS else int(re.sub(r"\D", "", token))

    levels: set[int] = set()
    for pattern in _LEVEL_REFERENCES:
        for match in pattern.finditer(text):
            phrase = match[1]
            levels.update(number(token[0]) for token in _NUMBER_TOKEN.finditer(phrase))
            for span in _NUMBER_RANGE.finditer(phrase):
                left, right = number(span[1]), number(span[2])
                # Un número arbitrario no debe producir un rango de tamaño ilimitado.
                if max(left, right) <= final_level:
                    levels.update(range(min(left, right), max(left, right) + 1))
    return levels


def project_chunk(chunk: Chunk, text: str, **metadata) -> Chunk:
    """Copia verificable: conserva source/page/id/version y no modifica el corpus."""
    return chunk.model_copy(update={
        "text": text,
        "hash": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "n_words": len(text.split()),
        "is_excerpt": True,
        "source_hash": chunk.source_hash or chunk.hash,
        **metadata,
    })


def boss_evidence_line(row: BossRow) -> str:
    """Una fila autorizada, sin las apariciones ni la descripción de otros niveles."""
    quest = "1st" if row.quest == "first" else "2nd"
    return (f"Name: {row.name} | HP: {row.hp} | Damage: {row.damage} | "
            f"Description: {quest} Quest: {row.level} (Boss).")


class ContentPolicy:
    name = "g2_content"

    def __init__(self, games: dict[str, GameConfig]):
        self.games = games
        self.location_gate = LocationGate(games)

    def allows(self, chunk: Chunk, profile: Profile, game: str) -> bool:
        """Notas y consumidores sin proyección requieren acceso al texto completo."""
        projected = self.project(chunk, profile, game)
        return projected is not None and projected.text == chunk.text

    def _location_allowed(self, chunk: Chunk, loc: Location, profile: Profile, game: str) -> bool:
        return self.location_gate.allows(chunk.model_copy(update={"location": loc}), profile, game)

    def _rule_allowed(self, rule: ContentRule, chunk: Chunk, profile: Profile, game: str) -> bool:
        if not self._location_allowed(chunk, rule.requires, profile, game):
            return False
        if rule.after_stage is None:
            return True
        cfg, prog = self.games[game], profile.progress.get(game)
        return (isinstance(prog, LinearStageProgress) and prog.current_stage in (cfg.stages or [])
                and cfg.stage_index(prog.current_stage) > cfg.stage_index(rule.after_stage))

    @staticmethod
    def _blocks(chunk: Chunk) -> list[tuple[str, str]] | None:
        """Recupera límites comprobables, incluso el primer fragmento de fixed."""
        known = set(chunk.sections or [chunk.section])
        title, lines, result = chunk.section, [], []
        observed = set()
        for line in chunk.text.splitlines():
            heading = _HEADING.fullmatch(line)
            if heading:
                if heading[1] not in known:
                    return None
                if lines:
                    result.append((title, "\n".join(lines)))
                    observed.add(title)
                title, lines = heading[1], []
            else:
                lines.append(line)
        if lines:
            result.append((title, "\n".join(lines)))
            observed.add(title)
        if not known <= observed:
            return None
        return result

    def _section_location(self, cfg: GameConfig, chunk: Chunk, title: str) -> Location:
        path = tuple(title.split(" > ")) if title != "(intro)" else ()
        source = chunk.source.removeprefix(f"{chunk.origin}: ")
        loc = locate(cfg, source, Section(chunk.page, path, ""))
        extra = next((e for e in cfg.extra_sources if e.site == chunk.origin), None)
        if extra and loc == Location() and extra.unlocated == "restricted":
            loc.restricted = not (extra.general_headings and any(
                re.search(extra.general_headings, part) for part in path))
        # Metadatos explícitos (p. ej., una fila SQL) siguen siendo obligatorios.
        if loc == Location() and extra is None:
            return chunk.location
        return loc

    def _boss_rows(self, chunk: Chunk, body: str, profile: Profile, game: str) -> str:
        rows = parse_boss_rows(chunk.model_copy(update={"text": body}))
        return "\n".join(boss_evidence_line(row) for row in rows
                         if self._location_allowed(chunk, Location(quest=row.quest, level=row.level),
                                                   profile, game))

    def _level_list(self, rule: LevelListRule, chunk: Chunk, body: str,
                    profile: Profile, game: str) -> str:
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        explicit = [_EXPLICIT_LEVEL.fullmatch(line) for line in lines]
        if chunk.is_excerpt and all(explicit):
            rows = [(int(match[1]), match[2]) for match in explicit if match]
            if any(level not in rule.levels for level, _ in rows):
                return ""
        elif len(lines) == len(rule.levels) and all(line.startswith("- ") for line in lines):
            rows = list(zip(rule.levels, (line[2:] for line in lines), strict=True))
        else:
            # La posición de una lista cortada no permite inferir el nivel de una fila.
            return ""
        visible = [(level, text) for level, text in rows
                   if self._location_allowed(chunk, Location(quest=rule.quest, level=level), profile, game)]
        if len(visible) == len(rows):
            return body
        return "\n".join(f"- Level {level}: {text}" for level, text in visible)

    def _map_content(self, cfg: GameConfig, chunk: Chunk, body: str, loc: Location,
                     profile: Profile, game: str, *, section_closed: bool) -> str:
        """Filtra unidades completas; no conserva colas de celdas de origen desconocido.

        Fixed puede cortar cualquier borde. Structural/rows también dividen una
        línea si supera wN: su última celda de N palabras no prueba un límite.
        Las proyecciones previas ya contienen únicamente celdas delimitadas.
        """
        lines = body.splitlines()
        if loc.quest is None and not any(_MAP_CELL.match(line) for line in lines):
            # Introductorio de navegación, fuera de la tabla de una quest.
            return "\n".join(line for line in lines if all(
                self._location_allowed(chunk, Location(level=level), profile, game)
                for level in _referenced_levels(line, max(cfg.levels or [0]))))
        units: list[tuple[str, str, bool]] = []
        cell, parts = None, []
        for line in lines:
            match = _MAP_CELL.match(line)
            if match:
                if cell is not None:
                    units.append((cell, "\n".join(parts), True))
                cell, parts = match[1].upper(), [line]
            elif cell is not None:
                parts.append(line)
            # Una cola sin coordenada puede ocultar su nivel en el chunk anterior.
        if cell is not None:
            text = "\n".join(parts)
            size = re.search(r"^(?:structural|rows)-w(\d+)", chunk.chunker)
            complete = (chunk.is_excerpt or section_closed
                        or bool(size and len(text.split()) < int(size[1])))
            units.append((cell, text, complete))
        kept = []
        for cell, text, complete in units:
            if not complete:
                continue
            requirements = [Location(quest=loc.quest, level=level)
                            for level in _referenced_levels(text, max(cfg.levels or [0]))]
            requirements += [Location(quest=rule.quest, level=rule.level) for rule in cfg.map_cell_rules
                             if re.search(rule.source, chunk.source, re.I) and cell in rule.cells
                             and (loc.quest is None or loc.quest == rule.quest)]
            if all(self._location_allowed(chunk, required, profile, game) for required in requirements):
                kept.append(text)
        return "\n".join(kept)

    def project(self, chunk: Chunk, profile: Profile, game: str) -> Chunk | None:
        if chunk.game != game or game not in self.games:
            return None
        if profile.unrestricted:
            return chunk
        if not self.location_gate.allows(chunk, profile, game):
            return None
        cfg = self.games[game]
        if any(re.search(pattern, chunk.source) for pattern in cfg.complete_route_sources):
            prog = profile.progress.get(game)
            if (not isinstance(prog, LevelSetProgress)
                    or not set(cfg.levels or []) <= {*prog.completed_levels, prog.current_level}):
                return None
            # Las rutas de otra quest se mantienen cerradas aunque se domine la actual.
            if any(("1st Quest" in section and prog.quest != "first")
                   or ("2nd Quest" in section and prog.quest != "second") for section in chunk.sections):
                return None
        blocks = self._blocks(chunk)
        if blocks is None:
            return None
        kept: list[tuple[str, str, Location]] = []
        changed = False
        for block_index, (title, original) in enumerate(blocks):
            loc = self._section_location(cfg, chunk, title)
            if not self._location_allowed(chunk, loc, profile, game):
                changed = True
                continue
            body = original
            if any(re.search(pattern, chunk.source, re.I) for pattern in cfg.map_sources):
                body = self._map_content(cfg, chunk, body, loc, profile, game,
                                         section_closed=block_index < len(blocks) - 1)
            if cfg.boss_table_source and re.search(cfg.boss_table_source, chunk.source):
                body = self._boss_rows(chunk, body, profile, game)
            for rule in cfg.level_list_rules:
                if re.search(rule.source, chunk.source) and re.search(rule.section, title):
                    body = self._level_list(rule, chunk, body, profile, game)
            for rule in cfg.content_rules:
                if (not re.search(rule.source, chunk.source, re.I)
                        or not re.search(rule.section, title, re.I)
                        or self._rule_allowed(rule, chunk, profile, game)):
                    continue
                if ((chunk.chunker.startswith("fixed") and rule.conservative_window)
                        or re.search(rule.match, title, re.I)):
                    body = ""
                    break
                filtered = []
                for line in body.splitlines():
                    if rule.unit == "paragraph":
                        if not re.search(rule.match, line, re.I):
                            filtered.append(line)
                    else:
                        sentences = re.split(r"(?<=[.!?])\s+", line)
                        filtered.append(" ".join(s for s in sentences if not re.search(rule.match, s, re.I)))
                body = "\n".join(line for line in filtered if line.strip())
            changed |= body != original
            if body.strip():
                kept.append((title, body, loc))
        if not kept:
            return None
        if not changed:
            return chunk
        titles = list(dict.fromkeys(title for title, _, _ in kept))
        text = "\n".join(f"[{title}]\n{body}" for title, body, _ in kept)
        return project_chunk(chunk, text, section=titles[0], sections=titles, location=kept[0][2])
