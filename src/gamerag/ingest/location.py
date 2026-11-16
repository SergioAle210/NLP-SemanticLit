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
                values = {k: v for k, v in m.groupdict().items() if v}
                if "quest_number" in values:
                    values["quest"] = values.pop("quest_number")
                if "quest_name" in values:
                    found.pop("quest", None)
                elif "quest" in values:
                    found.pop("quest_name", None)
                found |= values

    loc = Location()
    quest = found.get("quest", found.get("quest_number"))
    if quest is not None and cfg.quests:  # "1" -> "first" según el orden de `quests` en la config
        loc.quest = cfg.quests[int(quest) - 1]
    if "quest_name" in found:
        name = str(found["quest_name"])
        loc.quest = next((q for q in (cfg.quests or []) if q.casefold() == name.casefold()), name)
    if "level" in found:
        loc.level = int(found["level"])
    if "act" in found:
        loc.act = int(found["act"])
    if "stage" in found:
        loc.stage = str(found["stage"])
        if m := re.match(r"(\d+)-", loc.stage):  # "2-3" -> acto 2 (otros formatos de etapa no tienen acto)
            loc.act = loc.act or int(m.group(1))
    return loc
