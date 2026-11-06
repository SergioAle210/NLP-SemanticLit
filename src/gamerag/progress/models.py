"""Perfil del usuario y progreso por juego (ver docs/contracts/access-and-guardrails.md).

Cada juego tiene su modelo de progreso, según `progress_model` en su config:
- `level_set` (Zelda): conjunto de mazmorras completadas + mazmorra actual + quest.
- `linear_stage` (Ninja Gaiden): etapa actual en el orden de la config.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from gamerag.games import GameConfig, ProgressModel

Role = Literal["player", "completionist", "admin"]


class LevelSetProgress(BaseModel):
    kind: Literal["level_set"] = "level_set"
    quest: str
    completed_levels: list[int] = []
    current_level: int | None = None


class LinearStageProgress(BaseModel):
    kind: Literal["linear_stage"] = "linear_stage"
    current_stage: str


Progress = Annotated[LevelSetProgress | LinearStageProgress, Field(discriminator="kind")]


class Profile(BaseModel):
    user_id: str = Field(pattern=r"^[a-z0-9_]+$")
    role: Role
    progress: dict[str, Progress] = {}  # game_id -> progreso
    hint_level: int = Field(default=1, ge=1, le=3)  # pistas escalonadas: 1 qué, 2 dónde, 3 ruta completa

    @property
    def unrestricted(self) -> bool:
        """`completionist` y `admin` ven todo (no se aplican gates de spoilers)."""
        return self.role in ("completionist", "admin")


def validate_profile(profile: Profile, games: dict[str, GameConfig]) -> None:
    """Verifica que el progreso sea coherente con la config de cada juego. Lanza ValueError si no."""
    for game_id, prog in profile.progress.items():
        cfg = games.get(game_id)
        if cfg is None:
            raise ValueError(f"{profile.user_id}: juego desconocido {game_id}")
        if prog.kind != cfg.progress_model.value:
            raise ValueError(f"{profile.user_id}/{game_id}: se esperaba progreso {cfg.progress_model.value}")
        if isinstance(prog, LevelSetProgress) and cfg.progress_model is ProgressModel.LEVEL_SET:
            if prog.quest not in (cfg.quests or []):
                raise ValueError(f"{profile.user_id}/{game_id}: quest inválida {prog.quest}")
            bad = [lv for lv in [*prog.completed_levels, prog.current_level] if lv is not None and lv not in cfg.levels]
            if bad:
                raise ValueError(f"{profile.user_id}/{game_id}: niveles inválidos {bad}")
        if isinstance(prog, LinearStageProgress) and prog.current_stage not in (cfg.stages or []):
            raise ValueError(f"{profile.user_id}/{game_id}: etapa inválida {prog.current_stage}")


def load_profiles(path: Path, games: dict[str, GameConfig]) -> dict[str, Profile]:
    """Carga y valida los perfiles sembrados (data/seed/profiles.json)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    profiles = {p["user_id"]: Profile.model_validate(p) for p in raw}
    for p in profiles.values():
        validate_profile(p, games)
    return profiles
