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

ToolName = Literal["search_documents", "query_game_facts", "next_available_levels", "update_progress"]


class ProgressModel(StrEnum):
    LEVEL_SET = "level_set"  # Zelda: conjunto de mazmorras completadas + quest
    LINEAR_STAGE = "linear_stage"  # Ninja Gaiden: etapa actual, orden total


class ManualRef(BaseModel):
    url: str
    local_path: Path


class GameConfig(BaseModel):
    game_id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str
    platform: str
    year: int
    aliases: list[str] = []
    snapshot_dir: Path
    manual: ManualRef | None = None

    progress_model: ProgressModel
    levels: list[int] | None = None
    quests: list[str] | None = None
    stages: list[str] | None = None

    location_from_title: str | None = None
    location_from_heading: str | None = None

    # Páginas del snapshot que no se indexan (p. ej. índices de navegación sin contenido).
    exclude_pages: list[str] = []

    tools: list[ToolName]

    @field_validator("location_from_title", "location_from_heading")
    @classmethod
    def _valid_regex(cls, v: str | None) -> str | None:
        if v is not None:
            re.compile(v)
        return v

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
