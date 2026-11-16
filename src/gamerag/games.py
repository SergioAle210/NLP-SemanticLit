"""Configuración por juego (`config/games/*.yaml`).

Todo lo que distingue a un juego de otro vive aquí: modelo de progreso, cómo derivar la
ubicación desde la wiki, herramientas habilitadas. El resto del pipeline es genérico.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from gamerag.ingest.models import Location

ToolName = Literal["search_documents", "query_game_facts", "next_available_levels", "update_progress"]


class ProgressModel(StrEnum):
    LEVEL_SET = "level_set"  # Zelda: conjunto de mazmorras completadas + quest
    LINEAR_STAGE = "linear_stage"  # Ninja Gaiden: etapa actual, orden total


class RewriteRule(BaseModel):
    match: str  # expresión regular (sin distinguir mayúsculas)
    replace: str  # reemplazo; admite referencias \1


class QueryExpansionConfig(BaseModel):
    """Glosario del juego para la transformación de consultas (retrieval/query_expansion.py)."""

    rewrites: list[RewriteRule] = []  # identificadores: "Level-3" -> "dungeon 3"
    synonyms: dict[str, list[str]] = {}  # término del jugador -> términos del juego (se agregan)

    @field_validator("rewrites")
    @classmethod
    def _valid_patterns(cls, v: list[RewriteRule]) -> list[RewriteRule]:
        for r in v:
            re.compile(r.match)
        return v


class ManualRef(BaseModel):
    url: str
    local_path: Path


class ExtraSource(BaseModel):
    """Una fuente adicional de texto para el juego (otra wiki), con su política de ubicación."""

    site: str  # nombre del sitio (carpeta bajo data/wiki_snapshot/)
    snapshot_dir: Path
    # restricted: lo que no traiga ubicación queda restringido (salvo `general_headings`); general: como la fuente
    # principal. Para fuentes sin ubicación en el título, usar siempre restricted.
    unlocated: Literal["restricted", "general"] = "restricted"
    general_headings: str | None = None  # regex de encabezados de contenido sin spoilers (p. ej. Gameplay|Reception)
    exclude_pages: list[str] = []
    # game: describe solo este titulo. franchise: sus paginas son de toda la saga (p. ej. "Bow" o "Link" mezclan
    # varios juegos), asi que NO entran a la segunda busqueda salvo `secondary_franchise` (riesgo de contaminacion).
    scope: Literal["game", "franchise"] = "game"


class ContentRule(BaseModel):
    """Acceso a un pasaje sensible dentro de una sección que también contiene ayuda general."""

    source: str
    section: str = ".*"
    match: str
    unit: Literal["sentence", "paragraph"] = "paragraph"
    conservative_window: bool = True  # fixed puede empezar a mitad del pasaje
    requires: Location = Location()
    after_stage: str | None = None  # desenlace: la etapa actual debe ser posterior, no igual

    @field_validator("source", "section", "match")
    @classmethod
    def _patterns_compile(cls, value: str) -> str:
        re.compile(value)
        return value


class LevelListRule(BaseModel):
    """Lista ordinal cuyas filas corresponden a niveles, en el orden de la fuente."""

    source: str
    section: str
    quest: str
    levels: list[int]

    @field_validator("source", "section")
    @classmethod
    def _patterns_compile(cls, value: str) -> str:
        re.compile(value)
        return value


class MapCellRule(BaseModel):
    """Ubicación de una celda cuyo enlace o dependencia no sobrevive en texto plano."""

    source: str
    quest: str
    cells: list[str]
    level: int

    @field_validator("source")
    @classmethod
    def _pattern_compiles(cls, value: str) -> str:
        re.compile(value)
        return value

    @field_validator("cells")
    @classmethod
    def _coordinates(cls, values: list[str]) -> list[str]:
        if not values or any(not re.fullmatch(r"[A-Z]-[1-9]\d*", value) for value in values):
            raise ValueError("cells requiere coordenadas de mapa, p. ej. E-1")
        return values


class GameConfig(BaseModel):
    game_id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str
    platform: str
    year: int
    aliases: list[str] = []
    snapshot_dir: Path
    manual: ManualRef | None = None
    extra_sources: list[ExtraSource] = []  # otras wikis (ver config/sources.yaml)

    progress_model: ProgressModel
    levels: list[int] | None = None
    quests: list[str] | None = None
    stages: list[str] | None = None

    # Ubicación por título de página (último componente), para wikis cuyos títulos no traen un número:
    # {"Inside the Deku Tree": {"level": 1}}. Tiene prioridad sobre las regex.
    title_locations: dict[str, dict[str, int | str]] = {}
    location_from_title: str | None = None
    location_from_heading: str | None = None

    # Páginas del snapshot que no se indexan (p. ej. índices de navegación sin contenido).
    exclude_pages: list[str] = []

    content_rules: list[ContentRule] = []
    level_list_rules: list[LevelListRule] = []
    boss_table_source: str | None = None
    # Los resúmenes completos de rutas tienen dependencias implícitas entre líneas.
    # Solo se abren para jugadores que conocen todos los niveles de su quest.
    complete_route_sources: list[str] = []
    map_sources: list[str] = []  # mapas agregados: interpretar referencias dungeon/level por celda
    map_cell_rules: list[MapCellRule] = []  # aliases y pasos de una ruta identificados en el snapshot

    # Glosario para reescribir/expandir consultas (vocabulario del jugador -> del juego).
    query_expansion: QueryExpansionConfig = QueryExpansionConfig()

    tools: list[ToolName]

    @field_validator("location_from_title", "location_from_heading", "boss_table_source")
    @classmethod
    def _valid_regex(cls, v: str | None) -> str | None:
        if v is not None:
            re.compile(v)
        return v

    @field_validator("map_sources")
    @classmethod
    def _map_patterns_compile(cls, values: list[str]) -> list[str]:
        for value in values:
            re.compile(value)
        return values

    @model_validator(mode="after")
    def _progress_fields_match_model(self) -> GameConfig:
        if self.progress_model is ProgressModel.LEVEL_SET:
            if not self.levels or not self.quests:
                raise ValueError("level_set requiere 'levels' y 'quests'")
        elif self.progress_model is ProgressModel.LINEAR_STAGE:
            if not self.stages:
                raise ValueError("linear_stage requiere 'stages'")
            if len(set(self.stages)) != len(self.stages):
                raise ValueError("'stages' tiene duplicados")
        if "next_available_levels" in self.tools and self.progress_model is not ProgressModel.LEVEL_SET:
            raise ValueError("next_available_levels solo aplica a juegos no lineales (level_set)")
        for rule in self.content_rules:
            if rule.after_stage is not None and rule.after_stage not in (self.stages or []):
                raise ValueError(f"after_stage desconocida: {rule.after_stage}")
            if rule.requires.level is not None and rule.requires.level not in (self.levels or []):
                raise ValueError(f"nivel requerido desconocido: {rule.requires.level}")
        for rule in self.level_list_rules:
            if rule.quest not in (self.quests or []) or not set(rule.levels) <= set(self.levels or []):
                raise ValueError("level_list_rules requiere quest y niveles del juego")
        for rule in self.map_cell_rules:
            if rule.quest not in (self.quests or []) or rule.level not in (self.levels or []):
                raise ValueError("map_cell_rules requiere quest y nivel del juego")
        return self

    def stage_index(self, stage: str) -> int:
        """Posición de una etapa en el orden total (solo linear_stage)."""
        if not self.stages:
            raise ValueError(f"{self.game_id} no usa etapas lineales")
        return self.stages.index(stage)


def load_game_config(path: Path) -> GameConfig:
    with path.open(encoding="utf-8") as f:
        return GameConfig.model_validate(yaml.safe_load(f))


def load_all_games(config_dir: Path) -> dict[str, GameConfig]:
    games = {}
    for path in sorted(config_dir.glob("*.yaml")):
        cfg = load_game_config(path)
        if cfg.game_id in games:
            raise ValueError(f"game_id duplicado: {cfg.game_id}")
        games[cfg.game_id] = cfg
    return games
