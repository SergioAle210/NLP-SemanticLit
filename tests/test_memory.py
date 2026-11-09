"""Descomposición de consulta, dreaming (verificación + procedencia) y fuga de notas (sin red)."""

import json

import pytest

from gamerag.agents.planner import QueryPlanner
from gamerag.dream import candidates, dream, verify_note, write_notes
from gamerag.graph import graph_from
from gamerag.guardrails.provenance import ProvenanceFilter, leaked_notes
from gamerag.ingest.models import Chunk, Location
from gamerag.llm import LLMClient
from gamerag.pipeline import Pipeline
from gamerag.progress.models import LevelSetProgress, Profile
from gamerag.retrieval.bm25 import BM25Index, load_chunks
from gamerag.settings import Settings
from gamerag.store import Store


def _chunk(cid, text, game="zelda1", loc=None, **kw):
    return Chunk(chunk_id=cid, text=text, source=f"Zelda/{cid}", page=0, version="r1", url="u", section="s",
                 sections=["s"], hash=f"h{cid}", chunker="t", n_words=len(text.split()), game=game,
                 location=Location(**(loc or {})), **kw)


CORPUS = [
    _chunk("compass", "The compass directs Link to the location of the Triforce in each dungeon."),
    _chunk("triforce", "There are eight pieces of the Triforce. All eight are required to enter Level 9."),
    _chunk("sword7", "The magic sword is found in Level 7.", loc={"level": 7, "quest": "first"}),
]
BY_ID = {c.chunk_id: c for c in CORPUS}
NOVICE = Profile(user_id="n", role="player",
                 progress={"zelda1": LevelSetProgress(quest="first", completed_levels=[1], current_level=2)})
CHIEF = Profile(user_id="c", role="completionist")


class _LevelGate:
    name = "g2_location"

    def allows(self, chunk, profile, game):
        prog = profile.progress.get(game)
        if profile.unrestricted or chunk.location.level is None or prog is None:
            return True
        return chunk.location.level in {*prog.completed_levels, prog.current_level}


class FakeAPI:
    def __init__(self, payload):
        self.payload, self.calls = payload, 0
        self.messages = self

    def create(self, **kw):
        from anthropic.types import Message

        self.calls += 1
        text = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return Message.model_validate({
            "id": "m", "type": "message", "role": "assistant", "model": kw["model"],
            "content": [{"type": "text", "text": text}], "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 100, "output_tokens": 20}})


def llm(tmp_path, payload):
    api = FakeAPI(payload)
    return LLMClient(Settings(root=tmp_path, _env_file=None), client=api), api


# --- planner ----------------------------------------------------------------------------------

def test_planner_returns_subqueries_capped(tmp_path):
    c, _ = llm(tmp_path, {"queries": ["a", "b", "c", "d"]})
    assert QueryPlanner(c, max_queries=3).plan("q") == ["a", "b", "c"]


def test_planner_fails_open(tmp_path):
    c, _ = llm(tmp_path, "not json")
    assert QueryPlanner(c).plan("original question") == ["original question"]


class _FixedPlanner:
    def __init__(self, qs):
        self.qs = qs

    def plan(self, question):
        return self.qs


def test_decomposition_unions_contexts_and_records_subqueries():
    base = Pipeline({"zelda1": BM25Index(CORPUS)}, top_k=1, candidates=5)
    g = graph_from(base, planner=_FixedPlanner(["compass Triforce location", "pieces of Triforce Level 9"]))
    state = g.run("compound question", "zelda1", CHIEF)
    assert set(state["trace"].context) == {"compass", "triforce"}  # top_k=1 por sub-pregunta; la unión cubre ambas
    assert [q["query"] for q in state["trace"].subqueries] == ["compass Triforce location",
                                                               "pieces of Triforce Level 9"]
    assert state["steps"][:4] == ["input", "route", "plan", "retrieve"]


def test_single_subquery_behaves_like_no_planner():
    base = Pipeline({"zelda1": BM25Index(CORPUS)}, top_k=2, candidates=5)
    g = graph_from(base, planner=_FixedPlanner(["compass Triforce"]))
    assert g.run("compass Triforce", "zelda1", CHIEF)["trace"].subqueries == []


# --- verificación de notas ------------------------------------------------------------------------

SRC = [CORPUS[0].text, CORPUS[1].text]


def test_verify_accepts_supported_note():
    assert verify_note("The compass shows the Triforce location. All eight pieces open Level 9.", SRC) is None


@pytest.mark.parametrize(("note", "reason"), [
    ("There are nine pieces of the Triforce 12.", "numbers_not_in_sources"),
    ("The compass was invented by Ganon.", "entities_not_in_sources"),
    ("Dungeons contain mysterious artifacts everywhere underground.", "low_overlap"),
])
def test_verify_rejects_unsupported_note(note, reason):
    assert verify_note(note, SRC).startswith(reason)


# --- dreaming ---------------------------------------------------------------------------------

def _trace(tid, cited, subs=2, outcome="answered", evidence=None):
    return {"trace_id": tid, "outcome": outcome, "cited": cited, "subqueries": [{"query": "x"}] * subs,
            "evidence": evidence or []}


def test_candidates_pick_multihop_and_rewrites_once():
    ts = [_trace("a", ["compass", "triforce"]), _trace("b", ["triforce", "compass"]),  # mismo conjunto: una sola
          _trace("c", ["sword7"], subs=0, evidence=[{"sufficient": False, "rewrite": "magic sword level"}]),
          _trace("d", ["compass"], subs=0), _trace("e", ["compass", "triforce"], outcome="abstained")]
    assert [(r, t["trace_id"]) for r, t in candidates(ts)] == [("multihop", "a"), ("rewrite", "c")]


def test_dream_writes_verified_notes_and_rejects_hallucinations(tmp_path):
    good = {"title": "Triforce and compass", "text": "The compass directs Link to the Triforce. "
            "All eight pieces are required to enter Level 9.", "questions": ["What shows the Triforce?"]}
    c, api = llm(tmp_path, good)
    notes, rejected = dream([_trace("a", ["compass", "triforce"])], BY_ID, c, "zelda1")
    assert len(notes) == 1 and not rejected and api.calls == 1
    n = notes[0]
    assert n.kind == "note" and n.derived_from == ["compass", "triforce"] and "Q: What shows" in n.text

    bad = dict(good, text="The compass was forged by Ganon in 1986.")
    c2, _ = llm(tmp_path / "x", bad)
    notes2, rejected2 = dream([_trace("a", ["compass", "triforce"])], BY_ID, c2, "zelda1")
    assert notes2 == [] and rejected2[0]["reason"].startswith(("numbers", "entities"))


def test_write_notes_is_idempotent(tmp_path):
    c, _ = llm(tmp_path, {"title": "T", "text": "The compass directs Link to the Triforce.", "questions": ["q"]})
    notes, _ = dream([_trace("a", ["compass", "triforce"])], BY_ID, c, "zelda1")
    path = tmp_path / "m" / "notes.jsonl"
    assert write_notes(path, notes) == 1 and write_notes(path, notes) == 1
    assert [x.chunk_id for x in load_chunks(path)] == [notes[0].chunk_id]


# --- procedencia y fuga -----------------------------------------------------------------------------

def _note(derived):
    return _chunk("note1", "Magic sword summary.", kind="note", derived_from=derived)


def test_note_inherits_the_most_restrictive_access_of_its_sources():
    base = [_LevelGate()]
    note = _note(["compass", "sword7"])
    f = ProvenanceFilter({**BY_ID, "note1": note}, base)
    assert f.allows(note, CHIEF, "zelda1")  # el completista ve todas las fuentes
    assert not f.allows(note, NOVICE, "zelda1")  # sword7 es del Level 7: la nota queda bloqueada
    assert not f.allows(_note(["missing"]), NOVICE, "zelda1")  # fuente desconocida: fallo cerrado
    assert not f.allows(_note([]), CHIEF, "zelda1")  # sin procedencia: bloqueada


def test_pipeline_never_delivers_a_note_whose_sources_are_blocked():
    note = _note(["compass", "sword7"])
    allbyid = {**BY_ID, "note1": note}
    base = [_LevelGate()]
    pipe = Pipeline({"zelda1": BM25Index([*CORPUS, note])}, candidates=10,
                    access_filters=[*base, ProvenanceFilter(allbyid, base)])
    assert "note1" not in pipe.ask("magic sword summary", "zelda1", NOVICE)[1].context
    assert "note1" in pipe.ask("magic sword summary", "zelda1", CHIEF)[1].context
    # la métrica de fuga detectaría una nota colada
    assert leaked_notes([note], allbyid, base, NOVICE, "zelda1") == ["note1"]
    assert leaked_notes([note], allbyid, base, CHIEF, "zelda1") == []


def test_store_persists_new_trace_fields(tmp_path):
    base = Pipeline({"zelda1": BM25Index(CORPUS)}, top_k=1, candidates=5)
    g = graph_from(base, planner=_FixedPlanner(["compass Triforce", "pieces Level 9"]))
    _, trace = g.ask("q", "zelda1", CHIEF)
    st = Store(tmp_path / "t.sqlite3")
    st.log_trace(trace)
    saved = st.all_traces("zelda1")[0]
    assert len(saved["subqueries"]) == 2 and saved["cited"] == trace.cited
