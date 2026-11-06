"""Tests de los contratos: perfiles, generación, guardrails y pipeline (docs/contracts/)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from gamerag.games import load_all_games
from gamerag.generation.base import ExtractiveGenerator, FallbackGenerator, format_context
from gamerag.guardrails.base import BasicInputGuard, CitationGuard, GameFilter, GuardResult
from gamerag.ingest.models import Chunk
from gamerag.pipeline import BLOCKED_MESSAGE, Pipeline
from gamerag.progress.models import LevelSetProgress, Profile, load_profiles, validate_profile
from gamerag.retrieval.bm25 import BM25Index, Hit
from gamerag.schemas import Answer, Source

ROOT = Path(__file__).resolve().parents[1]
GAMES = load_all_games(ROOT / "config" / "games")
PLAYER = Profile(user_id="p", role="player",
                 progress={"zelda1": LevelSetProgress(quest="first", completed_levels=[1], current_level=2)})


def _chunk(cid: str, text: str, game: str = "zelda1", **loc) -> Chunk:
    return Chunk(chunk_id=cid, text=text, source=f"Zelda/{cid}", page=0, version="revid:1", url="u",
                 section="s", sections=["s"], hash=f"h-{cid}", chunker="test", n_words=len(text.split()),
                 game=game, location=loc)


CORPUS = [
    _chunk("raft", "The raft crosses lakes and oceans from a dock.", level=3, quest="first"),
    _chunk("sword", "The white sword needs five heart containers."),
    _chunk("candle", "The blue candle burns bushes."),
    _chunk("bombs", "Bombs open hidden passages."),
    _chunk("ladder", "The ladder crosses small gaps.", level=4, quest="first"),
]


def _hits(*chunks: Chunk) -> list[Hit]:
    return [Hit(rank=i, score=1.0, chunk=c) for i, c in enumerate(chunks, 1)]


# --- perfiles -------------------------------------------------------------------------------

def test_seed_profiles_load_and_match_game_configs():
    profiles = load_profiles(ROOT / "data" / "seed" / "profiles.json", GAMES)
    assert set(profiles) == {"novato", "intermedio", "segunda_vuelta", "completionist", "admin"}
    assert profiles["completionist"].unrestricted and not profiles["novato"].unrestricted
    assert profiles["segunda_vuelta"].progress["zelda1"].quest == "second"


@pytest.mark.parametrize(("progress", "error"), [
    ({"zelda1": {"kind": "level_set", "quest": "third"}}, "quest"),
    ({"zelda1": {"kind": "level_set", "quest": "first", "completed_levels": [10]}}, "niveles"),
    ({"ninja_gaiden_nes": {"kind": "linear_stage", "current_stage": "7-1"}}, "etapa"),
    ({"ninja_gaiden_nes": {"kind": "level_set", "quest": "first"}}, "linear_stage"),
])
def test_invalid_progress_is_rejected(progress, error):
    with pytest.raises(ValueError, match=error):
        validate_profile(Profile(user_id="x", role="player", progress=progress), GAMES)


def test_hint_level_is_bounded():
    with pytest.raises(ValidationError):
        Profile(user_id="x", role="player", hint_level=4)


# --- generación -----------------------------------------------------------------------------

def test_extractive_cites_context_and_abstains_without_it():
    ans = ExtractiveGenerator(max_excerpts=2).generate("q", _hits(*CORPUS[:3]), game="zelda1", trace_id="t")
    assert not ans.abstained
    assert [s.chunk_id for s in ans.sources] == ["raft", "sword"]
    empty = ExtractiveGenerator().generate("q", [], game="zelda1", trace_id="t")
    assert empty.abstained and empty.sources == []


def test_format_context_delimits_chunks_as_data():
    ctx = format_context(_hits(CORPUS[0]))
    assert ctx.startswith('<document chunk_id="raft"') and ctx.endswith("</document>")


class _Broken:
    name = "broken"

    def generate(self, question, context, *, game, trace_id):
        raise TimeoutError("API down")


def test_fallback_degrades_to_extractive_and_flags_review():
    gen = FallbackGenerator(_Broken())
    ans = gen.generate("q", _hits(CORPUS[0]), game="zelda1", trace_id="t")
    assert ans.needs_human_review and [s.chunk_id for s in ans.sources] == ["raft"]
    assert "TimeoutError" in gen.last_error


# --- guardrails -----------------------------------------------------------------------------

def test_basic_input_guard():
    g = BasicInputGuard(max_chars=10)
    assert g.check("ok?", PLAYER).allowed
    assert g.check("   ", PLAYER).reason == "empty_question"
    assert not g.check("x" * 11, PLAYER).allowed


def test_game_filter_is_g1():
    assert GameFilter().allows(CORPUS[0], PLAYER, "zelda1")
    assert not GameFilter().allows(_chunk("ng", "x", game="ninja_gaiden_nes"), PLAYER, "zelda1")


def test_citation_guard_rejects_citations_outside_context():
    ctx = _hits(CORPUS[0])
    good = Answer(answer="a", sources=[Source(source="s", page=0, chunk_id="raft")], abstained=False,
                  game="zelda1", trace_id="t")
    bad = good.model_copy(update={"sources": [Source(source="s", page=0, chunk_id="ladder")]})
    assert CitationGuard().check(good, ctx, PLAYER).allowed
    assert "citations_outside_context" in CitationGuard().check(bad, ctx, PLAYER).reason


# --- pipeline -------------------------------------------------------------------------------

class _LevelGate:
    """Gate de ejemplo (G2 simplificado) para probar el enganche: bloquea mazmorras no alcanzadas."""

    name = "g2_location"

    def allows(self, chunk, profile, game):
        prog = profile.progress.get(game)
        if profile.unrestricted or chunk.location.level is None or prog is None:
            return True
        return chunk.location.level in {*prog.completed_levels, prog.current_level}


def _pipeline(**kw) -> Pipeline:
    return Pipeline({"zelda1": BM25Index(CORPUS)}, top_k=2, candidates=5, **kw)


def test_pipeline_answers_with_trace():
    ans, trace = _pipeline().ask("How do I cross the oceans with the raft?", "zelda1", PLAYER)
    assert trace.outcome == "answered" and trace.context[0] == "raft"
    assert ans.trace_id == trace.trace_id and ans.sources[0].chunk_id == "raft"
    assert set(trace.latency_ms) == {"input", "retrieval", "access", "generation", "output"}


def test_pipeline_access_filter_hook_blocks_and_records():
    pipe = _pipeline(access_filters=[GameFilter(), _LevelGate()])
    ans, trace = pipe.ask("raft oceans dock", "zelda1", PLAYER)  # el raft es del Level-3, aún no alcanzado
    assert "raft" not in trace.context
    assert next(c for c in trace.candidates if c.chunk_id == "raft").blocked_by == "g2_location"
    unrestricted = Profile(user_id="c", role="completionist")
    assert "raft" in pipe.ask("raft oceans dock", "zelda1", unrestricted)[1].context


def test_pipeline_reports_blocked_by_access_when_everything_is_gated():
    # Solo el raft (Level-3) y la ladder (Level-4) contienen los términos, y ambos están bloqueados.
    pipe = Pipeline({"zelda1": BM25Index(CORPUS)}, access_filters=[_LevelGate()], candidates=5)
    ans, trace = pipe.ask("raft ladder", "zelda1", PLAYER)
    assert ans.blocked_by_spoiler and ans.abstained and ans.answer == BLOCKED_MESSAGE
    assert trace.outcome == "blocked_by_access"


def test_pipeline_input_and_output_guard_hooks():
    ans, trace = _pipeline().ask("   ", "zelda1", PLAYER)
    assert trace.outcome == "rejected_input" and ans.abstained

    class _Reject:
        name = "always_reject"

        def check(self, answer, context, profile):
            return GuardResult(False, "test")

    ans, trace = _pipeline(output_guards=[_Reject()]).ask("raft", "zelda1", PLAYER)
    assert trace.outcome == "rejected_output" and ans.needs_human_review and trace.output_guards == {
        "always_reject": "test"}


def test_pipeline_rejects_unknown_game():
    with pytest.raises(ValueError, match="no disponible"):
        _pipeline().ask("q", "mario", PLAYER)
