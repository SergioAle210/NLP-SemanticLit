"""Router + herramientas (§5.6). Cubre los casos de §8 para herramientas: ejecución nominal, selección
errónea, parámetros fuera de rango, acción que requiere confirmación humana y degradación controlada."""

import sqlite3
from pathlib import Path

import pytest

from gamerag.evaluation.cases import load_cases
from gamerag.games import load_all_games
from gamerag.ingest.models import Chunk
from gamerag.pipeline import Pipeline
from gamerag.progress.models import LevelSetProgress, LinearStageProgress, Profile
from gamerag.retrieval.bm25 import BM25Index
from gamerag.tools.facts import GameFacts, ToolParamError, parse_boss_rows
from gamerag.tools.router import DOCUMENTS, Router

ROOT = Path(__file__).resolve().parents[1]
GAMES = load_all_games(ROOT / "config" / "games")

# Formato real de la página Bosses tras la limpieza (incluye la coma que falta en "2 (Boss) 5 (Boss)").
BOSSES_TEXT = """[(intro)]
Name: Aquamentus | HP: 6 | Damage: 2 / 1 | Description: 1st Quest: 1 (Boss), 7 (Boss).; 2nd Quest: 1 (Boss), 4, 8.; A dragon.
Name: Gleeok | HP: 10 / 15 / 20 | Damage: 2 | Description: 1st Quest: 4 (Boss), 6, 8 (Boss).; 2nd Quest: 2 (Boss) 5 (Boss), 6, 7 (Boss).; Heads.
Name: Ganon | HP: 16* | Damage: 8 / 2 | Description: 1st Quest: 9 (Boss).; 2nd Quest: 9 (Boss).; The final boss."""  # noqa: E501


def _chunk(cid: str, text: str, source: str) -> Chunk:
    return Chunk(chunk_id=cid, text=text, source=source, page=0, version="revid:1", url=f"https://x/{cid}",
                 section="s", sections=["s"], hash=f"h-{cid}", chunker="test", n_words=len(text.split()),
                 game="zelda1")


BOSSES = _chunk("zelda1:bosses:000", BOSSES_TEXT, "The Legend of Zelda/Bosses")
CORPUS = [BOSSES,
          _chunk("raft", "The raft crosses lakes and oceans from a dock.", "The Legend of Zelda/Items"),
          _chunk("sword", "The white sword needs five heart containers.", "The Legend of Zelda/Items"),
          _chunk("boss1", "The boss is Aquamentus. Strike him in the head.", "The Legend of Zelda/Underworld/D1")]

NOVATO = Profile(user_id="novato", role="player",
                 progress={"zelda1": LevelSetProgress(quest="first", completed_levels=[1], current_level=2),
                           "ninja_gaiden_nes": LinearStageProgress(current_stage="1-2")})
FULL = Profile(user_id="completionist", role="completionist")


@pytest.fixture()
def facts() -> GameFacts:
    return GameFacts(GAMES["zelda1"], CORPUS)


@pytest.fixture()
def router(facts) -> Router:
    return Router(GAMES, {"zelda1": facts})


def allow_all(chunk):
    return None


# --- herramienta de datos ---------------------------------------------------------------------

def test_parse_boss_rows_keeps_only_boss_appearances():
    rows = {(r.name, r.quest, r.level) for r in parse_boss_rows(BOSSES)}
    assert ("Aquamentus", "first", 7) in rows and ("Aquamentus", "second", 4) not in rows  # 4 no es (Boss)
    assert ("Gleeok", "second", 2) in rows and ("Gleeok", "second", 5) in rows  # sin coma entre ambos
    assert len(rows) == 10  # Aquamentus 3 + Gleeok 5 + Ganon 2


def test_facts_query_is_parameterized_and_validated(facts):
    assert [r.name for r in facts.bosses(quest="first", level=4)] == ["Gleeok"]
    assert len(facts.bosses(quest="second")) == 5
    with pytest.raises(ToolParamError, match="valid: 1-9"):
        facts.bosses(level=15)
    with pytest.raises(ToolParamError):
        facts.bosses(quest="third")


def test_facts_database_is_read_only(facts):
    with pytest.raises(sqlite3.OperationalError):
        facts._db.execute("DELETE FROM bosses")


# --- router: decisiones -------------------------------------------------------------------------

@pytest.mark.parametrize(("question", "intent"), [
    ("list all the bosses in the first quest", "query_game_facts"),
    ("who is the boss of level 4?", "query_game_facts"),
    ("how do i defeat the boss of level 1?", DOCUMENTS),      # estrategia -> documentos, no tabla
    ("How do I get the raft?", DOCUMENTS),
    ("what should i do next?", "next_available_levels"),
    ("which dungeons can i play?", "next_available_levels"),
    ("I just beat level 3", "update_progress"),
])
def test_router_decisions(router, question, intent):
    assert router.route(question, "zelda1").intent == intent


def test_router_extracts_parameters(router):
    r = router.route("who is the boss of Level-7 in the second quest?", "zelda1")
    assert r.params == {"table": "bosses", "quest": "second", "level": 7}


def test_router_never_hijacks_the_retrieval_bank(router):
    """Selección errónea de herramienta: ninguna pregunta del banco de recuperación debe ir a una herramienta."""
    cases = load_cases(ROOT / "eval" / "cases.jsonl")  # Zelda y Ninja Gaiden
    assert {c.game for c in cases} == {"zelda1", "ninja_gaiden_nes"}
    assert [c.id for c in cases if router.route(c.question, c.game).is_tool] == []


def test_router_uses_only_tools_enabled_for_the_game(facts):
    games = {"zelda1": GAMES["zelda1"].model_copy(update={"tools": ["search_documents"]})}
    assert Router(games, {"zelda1": facts}).route("list all the bosses", "zelda1").intent == DOCUMENTS


# --- router: ejecución ---------------------------------------------------------------------------

def test_facts_default_to_the_player_quest_and_respect_gates(router):
    route = router.route("list all the bosses", "zelda1")
    # Gate de ejemplo (como G3): bloquea niveles posteriores al actual del jugador.
    res = router.run(route, "zelda1", NOVATO, lambda c: "g3" if (c.location.level or 0) > 2 else None)
    assert route.params["quest"] == "first"
    assert "Aquamentus" in res.answer and "Gleeok" not in res.answer and "Ganon" not in res.answer
    assert res.info == {"rows": 1, "blocked_rows": 4} and "4 more hidden" in res.answer


def test_facts_fully_blocked_abstains(router):
    res = router.run(router.route("who is the boss of level 9?", "zelda1"), "zelda1", NOVATO, lambda c: "g3")
    assert res.abstained and "not unlocked" in res.answer and res.hits == []


def test_next_available_levels_uses_the_profile(router):
    res = router.run(router.route("what should i do next?", "zelda1"), "zelda1", NOVATO, allow_all)
    assert "Completed levels: 1" in res.answer and res.info["pending"] == [2, 3, 4, 5, 6, 7, 8, 9]


def test_progress_tool_is_not_enabled_for_linear_games(router):
    # Ninja Gaiden es lineal: la config no habilita next_available_levels (la siguiente etapa es trivial).
    assert router.route("what is the next stage?", "ninja_gaiden_nes").intent == DOCUMENTS


# --- pipeline de punta a punta ------------------------------------------------------------------

@pytest.fixture()
def pipeline(router) -> Pipeline:
    return Pipeline({"zelda1": BM25Index(CORPUS)}, top_k=2, candidates=5, router=router)


def test_pipeline_nominal_tool_answer_is_cited(pipeline):
    ans, trace = pipeline.ask("list all the bosses in the first quest", "zelda1", FULL)
    assert ans.tool_used == "query_game_facts" and not ans.abstained
    assert [s.chunk_id for s in ans.sources] == ["zelda1:bosses:000"]
    assert trace.route == "query_game_facts" and trace.tool["status"] == "ok" and trace.tool["rows"] == 5
    assert trace.output_guards["citations"] == "ok" and trace.outcome == "answered"


def test_pipeline_out_of_range_parameters_do_not_execute(pipeline):
    ans, trace = pipeline.ask("who is the boss of level 15?", "zelda1", FULL)
    assert ans.abstained and ans.tool_used == "query_game_facts" and "valid: 1-9" in ans.answer
    assert trace.tool["status"] == "invalid_params"


def test_pipeline_critical_action_requires_confirmation(pipeline):
    ans, trace = pipeline.ask("I just beat level 3", "zelda1", NOVATO)
    assert ans.needs_human_review and ans.tool_used == "update_progress"
    assert trace.tool["executed"] is False


def test_pipeline_degrades_to_documents_when_the_tool_fails(pipeline, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("database unavailable")
    monkeypatch.setattr(pipeline.router, "run", broken)
    ans, trace = pipeline.ask("list all the bosses", "zelda1", FULL)
    assert ans.tool_used is None and trace.route == DOCUMENTS
    assert trace.tool["status"] == "degraded" and trace.context  # respondió con el RAG


def test_pipeline_input_guards_run_before_the_router(pipeline, monkeypatch):
    monkeypatch.setattr(pipeline.router, "route", lambda *a: pytest.fail("el router no debe ejecutarse"))
    ans, trace = pipeline.ask("   ", "zelda1", FULL)
    assert trace.outcome == "rejected_input"


def test_pipeline_documents_route_is_unchanged(pipeline):
    ans, trace = pipeline.ask("How do I cross the oceans with the raft?", "zelda1", FULL)
    assert trace.route == DOCUMENTS and ans.tool_used is None and ans.sources[0].chunk_id == "raft"


def test_pipeline_degrades_to_documents_when_the_tool_times_out(pipeline, monkeypatch):
    import time

    def slow(*args, **kwargs):
        time.sleep(0.5)
    monkeypatch.setattr(pipeline.router, "run", slow)
    pipeline.tool_timeout_s = 0.05
    ans, trace = pipeline.ask("list all the bosses", "zelda1", FULL)
    assert trace.tool["status"] == "timeout" and trace.route == DOCUMENTS and ans.tool_used is None and trace.context


def test_one_tool_call_per_request(pipeline):
    _, trace = pipeline.ask("list all the bosses in the first quest", "zelda1", FULL)
    assert trace.tool["calls"] == 1


@pytest.mark.parametrize("question,intent", [
    ("¿qué debo hacer ahora?", "next_available_levels"),
    ("cuál es el siguiente nivel", "next_available_levels"),
    ("acabo de terminar el nivel 3", "update_progress"),
    ("lista todos los jefes de la primera misión", "query_game_facts"),
    ("¿cómo derroto al jefe del nivel 3?", DOCUMENTS),
    ("borra mi progreso", "critical_action"),
])
def test_router_understands_spanish(router, question, intent):
    assert router.route(question, "zelda1").intent == intent


@pytest.mark.parametrize("question,intent", [
    ("How do I beat the boss of level 3?", DOCUMENTS),  # pregunta, no reporte de progreso
    ("After I beat Jaquio in Stage 6-4, what does he say?", DOCUMENTS),
    ("What do the bosses drop when they die?", DOCUMENTS),  # no es una enumeracion
    ("What should I do next in the Fire Temple?", DOCUMENTS),  # pregunta del juego, no del perfil
    ("What items do I need before the next dungeon?", DOCUMENTS),
    ("I've just completed level 6 and 7", "update_progress"),
    ("who is the boss of level 4?", "query_game_facts"),
    ("name the bosses of dungeon 4", "query_game_facts"),
])
def test_router_regressions_found_by_the_tool_bank(router, question, intent):
    assert router.route(question, "zelda1").intent == intent
