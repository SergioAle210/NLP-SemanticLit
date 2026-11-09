"""Gate G2 (ubicación) para Zelda (level_set) y Ninja Gaiden (linear_stage), con las configs reales."""

from pathlib import Path

import pytest

from gamerag.games import load_all_games
from gamerag.guardrails.location import LocationGate
from gamerag.ingest.models import Chunk, Location
from gamerag.progress.models import LevelSetProgress, LinearStageProgress, Profile

GAMES = load_all_games(Path(__file__).resolve().parents[1] / "config" / "games")
GATE = LocationGate(GAMES)


def _chunk(game="zelda1", **loc) -> Chunk:
    return Chunk(chunk_id="c", text="t", source="s", page=0, version="r", url="u", section="s", sections=["s"],
                 hash="h", chunker="t", n_words=1, game=game, location=Location(**loc))


def _zelda(quest="first", done=(1,), current=2) -> Profile:
    return Profile(user_id="p", role="player",
                   progress={"zelda1": LevelSetProgress(quest=quest, completed_levels=list(done),
                                                        current_level=current)})


def _ng(stage) -> Profile:
    return Profile(user_id="p", role="player", progress={"ninja_gaiden_nes": LinearStageProgress(current_stage=stage)})


@pytest.mark.parametrize(("loc", "allowed"), [
    ({}, True),  # contenido general
    ({"level": 1, "quest": "first"}, True),  # completada
    ({"level": 2, "quest": "first"}, True),  # actual
    ({"level": 3, "quest": "first"}, False),  # aún no alcanzada
    ({"level": 1, "quest": "second"}, False),  # otra quest
    ({"quest": "second"}, False),  # contenido de la segunda quest, sin nivel
    ({"quest": "first"}, True),
])
def test_zelda_level_set(loc, allowed):
    assert GATE.allows(_chunk(**loc), _zelda(), "zelda1") is allowed


@pytest.mark.parametrize(("stage", "allowed"), [
    ("1-1", True), ("1-2", True), ("2-1", False), ("6-5", False),
])
def test_ninja_gaiden_stage_order(stage, allowed):
    assert GATE.allows(_chunk("ninja_gaiden_nes", act=int(stage[0]), stage=stage), _ng("1-2"), "ninja_gaiden_nes") \
        is allowed


def test_ninja_gaiden_act_only_chunk_uses_the_current_act():
    assert GATE.allows(_chunk("ninja_gaiden_nes", act=2), _ng("2-1"), "ninja_gaiden_nes")
    assert not GATE.allows(_chunk("ninja_gaiden_nes", act=3), _ng("2-3"), "ninja_gaiden_nes")


def test_unrestricted_roles_see_everything():
    for role in ("completionist", "admin"):
        p = Profile(user_id="x", role=role)
        assert GATE.allows(_chunk(level=9, quest="second"), p, "zelda1")


def test_fails_closed_without_known_progress():
    p = Profile(user_id="x", role="player")  # jugador sin progreso registrado
    assert GATE.allows(_chunk(), p, "zelda1")  # lo general sí
    assert not GATE.allows(_chunk(level=1, quest="first"), p, "zelda1")
    assert not GATE.allows(_chunk("ninja_gaiden_nes", act=1, stage="1-1"), p, "ninja_gaiden_nes")


def test_unknown_stage_in_progress_or_chunk_blocks():
    bad = Profile(user_id="x", role="player",
                  progress={"ninja_gaiden_nes": LinearStageProgress(current_stage="9-9")})
    assert not GATE.allows(_chunk("ninja_gaiden_nes", act=1, stage="1-1"), bad, "ninja_gaiden_nes")
    assert not GATE.allows(_chunk("ninja_gaiden_nes", act=1, stage="7-7"), _ng("6-5"), "ninja_gaiden_nes")
