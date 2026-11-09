"""Deriva la ubicación en el juego (metadatos de acceso) a partir de la wiki.

Usa las expresiones regulares de la config del juego:
- `location_from_title`: sobre el título de la página (Zelda: "Underworld/Quest 1/Dungeon 4").
- `location_from_heading`: sobre los encabezados de la sección (Ninja Gaiden: "Stage 2-3").
"""

from __future__ import annotations

import re

from gamerag.games import GameConfig
from gamerag.ingest.models import Location
from gamerag.ingest.sections import Section


def locate(cfg: GameConfig, page_title: str, section: Section) -> Location:
    found: dict[str, str | int] = {}
    if explicit := cfg.title_locations.get(page_title.rsplit("/", 1)[-1]):
        found |= explicit
    if cfg.location_from_title and (m := re.search(cfg.location_from_title, page_title)):
        found |= {k: v for k, v in m.groupdict().items() if v}
    if cfg.location_from_heading:
        for heading in section.path:  # el encabezado más profundo que coincida gana
            if m := re.search(cfg.location_from_heading, heading):
                found |= {k: v for k, v in m.groupdict().items() if v}

    loc = Location()
    if "quest" in found and cfg.quests:  # "1" -> "first" según el orden de `quests` en la config
        loc.quest = cfg.quests[int(found["quest"]) - 1]
    if "quest_name" in found:
        loc.quest = str(found["quest_name"])
    if "level" in found:
        loc.level = int(found["level"])
    if "act" in found:
        loc.act = int(found["act"])
    if "stage" in found:
        loc.stage = str(found["stage"])
        if m := re.match(r"(\d+)-", loc.stage):  # "2-3" -> acto 2 (otros formatos de etapa no tienen acto)
            loc.act = loc.act or int(m.group(1))
    return loc
