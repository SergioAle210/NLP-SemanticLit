"""Gate G2: contenido de ubicaciones que el jugador todavía no alcanza (docs/contracts/access-and-guardrails.md).

- **Zelda (`level_set`)**: el chunk de una mazmorra solo es visible si su `level` está en
  `completed_levels ∪ {current_level}`; un chunk con `quest` solo si coincide con la quest del jugador.
- **Ninja Gaiden (`linear_stage`)**: visible si su etapa es `<= current_stage` en el orden de la config; si el
  chunk solo trae el acto, si `act <=` el acto actual.
- Contenido general (sin ubicación) es siempre visible. `completionist` y `admin` no tienen restricción.
- **Fallo cerrado:** un jugador sin progreso registrado para el juego, o con progreso de otro tipo, solo ve
  contenido general; una etapa fuera de la config bloquea.
"""

from __future__ import annotations

from gamerag.games import GameConfig
from gamerag.ingest.models import Chunk
from gamerag.progress.models import LevelSetProgress, LinearStageProgress, Profile


class LocationGate:
    name = "g2_location"

    def __init__(self, games: dict[str, GameConfig]):
        self.games = games

    def allows(self, chunk: Chunk, profile: Profile, game: str) -> bool:
        if profile.unrestricted:
            return True
        loc = chunk.location
        if loc.restricted:
            return False  # sin ubicación asignada: solo perfiles sin restricción
        if loc.level is None and loc.quest is None and loc.act is None and loc.stage is None:
            return True  # contenido general
        prog = profile.progress.get(game)
        if isinstance(prog, LevelSetProgress):
            if loc.quest is not None and loc.quest != prog.quest:
                return False
            return loc.level is None or loc.level in {*prog.completed_levels, prog.current_level}
        if isinstance(prog, LinearStageProgress):
            cfg = self.games.get(game)
            if cfg is None or not cfg.stages or prog.current_stage not in cfg.stages:
                return False
            current = cfg.stage_index(prog.current_stage)
            if loc.stage is not None:
                return loc.stage in cfg.stages and cfg.stage_index(loc.stage) <= current
            if loc.act is not None:
                head = prog.current_stage.split("-")[0]
                return head.isdigit() and loc.act <= int(head)
            return True
        return False  # sin progreso conocido para este juego
