"""Métricas de diagnóstico, explicación por respuesta y puerta de regresión del marcador (sin red)."""

import copy

import pytest

from gamerag.evaluation.cases import EvalCase
from gamerag.evaluation.diagnostics import (
    aggregate,
    case_diagnostics,
    groundedness,
    ndcg_at_k,
    novel_number,
    redundancy,
)
from gamerag.evaluation.scorecard import check
from gamerag.explain import explain
from gamerag.ingest.models import Chunk
from gamerag.pipeline import CandidateTrace, Trace
from gamerag.schemas import Answer, Source


def _chunk(cid, text, source="S"):
    return Chunk(chunk_id=cid, text=text, source=source, page=0, version="r", url="u", section="s", sections=["s"],
                 hash=cid, chunker="t", n_words=len(text.split()), game="g")


def _case(answerable=True, evidence=(("white sword",), ("five heart containers",))):
    kw = dict(id="c", question="q", expected_behavior="b", expected_sources=["S"] if answerable else [],
              expected_pages=[0] if answerable else [], answerable=answerable, risk_level="low", category="direct",
              game="g", profile="p", evidence=[list(e) for e in evidence] if answerable else [])
    return EvalCase(**kw)


CHUNKS = {c.chunk_id: c for c in [
    _chunk("a", "The white sword needs five heart containers to be obtained from the old man."),
    _chunk("b", "Bombs open hidden passages in dungeon walls."),
    _chunk("c", "Rupees are the currency used in shops across the overworld."),
]}


def test_ndcg_rewards_early_relevance():
    assert ndcg_at_k([True, False, False], 5) == 1.0
    assert 0 < ndcg_at_k([False, False, True], 5) < ndcg_at_k([False, True, False], 5) < 1.0
    assert ndcg_at_k([False, False], 5) == 0.0


def test_redundancy_is_high_for_repeated_chunks():
    twin = [_chunk("x", "white sword hearts old man"), _chunk("y", "white sword hearts old man")]
    assert redundancy(twin) == 1.0 and redundancy([CHUNKS["a"], CHUNKS["c"]]) < 0.2


def test_groundedness_flags_unsupported_sentences():
    g, uns = groundedness("The white sword needs five heart containers. A dragon guards the secret volcano treasure.",
                          [CHUNKS["a"]])
    assert 0.3 < g < 0.8 and uns == 0.5
    full, none_unsupported = groundedness("The white sword needs five heart containers.", [CHUNKS["a"]])
    assert full == 1.0 and none_unsupported == 0.0


def test_novel_number_detects_invented_figures():
    assert novel_number("You need 9 heart containers.", [CHUNKS["a"]])
    assert not novel_number("It needs five heart containers.", [CHUNKS["a"]])


def test_case_diagnostics_for_a_grounded_answer():
    row = {"context": ["b", "a", "c"], "sources": ["a"], "abstained": False,
           "answer": "The white sword needs five heart containers."}
    d = case_diagnostics(_case(), row, CHUNKS)
    assert d["recall"] == 1.0 and d["mrr"] == 0.5 and d["coverage"] == 1.0 and d["cite_recall"] == 1.0
    assert d["noise"] == pytest.approx(2 / 3) and d["answered_without_evidence"] is False
    assert d["groundedness"] == 1.0 and d["novel_number"] is False


def test_answering_without_evidence_is_flagged():
    row = {"context": ["b", "c"], "sources": ["b"], "abstained": False, "answer": "It needs nine hearts."}
    d = case_diagnostics(_case(), row, CHUNKS)
    assert d["recall"] == 0.0 and d["answered_without_evidence"] is True


def test_abstention_precision_recall_and_overconfidence():
    unans = _case(answerable=False)
    d = [case_diagnostics(unans, {"context": [], "abstained": True}, CHUNKS),
         case_diagnostics(unans, {"context": [], "abstained": False, "answer": "Sure, it is in level nine."}, CHUNKS),
         case_diagnostics(_case(), {"context": ["a"], "sources": [], "abstained": True}, CHUNKS)]
    agg = aggregate(d)
    assert agg["abstain_recall"] == 0.5 and agg["overconfident_rate"] == 0.5
    assert agg["abstain_precision"] == 0.5 and agg["false_abstain_rate"] == 1.0


def test_abstention_precision_is_undefined_without_unanswerable_cases():
    agg = aggregate([case_diagnostics(_case(), {"context": ["a"], "sources": ["a"], "abstained": True}, CHUNKS)])
    assert agg["abstain_precision"] is None and agg["false_abstain_rate"] == 1.0


# --- explicación -------------------------------------------------------------------------------

def _trace(**kw):
    base = dict(trace_id="t", question="q", game="g", user_id="u", role="player", retriever="r", generator="x")
    return Trace(**(base | kw))


def test_explanation_of_a_grounded_answer_does_not_leak_blocked_content():
    tr = _trace(route="documents", outcome="answered", context=["a"], cited=["a"],
                candidates=[CandidateTrace(rank=1, chunk_id="a", score=1.0),
                            CandidateTrace(rank=2, chunk_id="secret-boss-page", score=0.9, blocked_by="g2_location")])
    ans = Answer(answer="x", sources=[Source(source="Zelda/Items", page=0, chunk_id="a")], abstained=False, game="g",
                 trace_id="t")
    ex = explain(tr, ans)
    assert ex["complete"] and "Zelda/Items" in ex["summary"] and "1 fragmentos" in ex["summary"]
    assert "secret-boss-page" not in str(ex)  # solo cuenta y nombre del control, nunca el contenido bloqueado
    stage = next(s for s in ex["steps"] if s["stage"] == "recuperación")
    assert stage["bloqueados"] == {"contenido que aún no has desbloqueado": 1}


def test_explanation_of_abstention_and_rejection():
    ab = explain(_trace(route="documents", outcome="abstained",
                        evidence=[{"sufficient": False, "reason": "off-topic", "rewrite": "", "query": "q"}]),
                 Answer(answer="x", abstained=True, game="g", trace_id="t"))
    assert "no contiene evidencia suficiente" in ab["summary"] and "off-topic" in ab["summary"] and ab["complete"]
    rej = explain(_trace(route="documents", outcome="rejected_input", input_guards={"injection": "prompt_injection:x"}),
                  Answer(answer="x", abstained=True, game="g", trace_id="t"))
    assert "validaciones de entrada" in rej["summary"] and not rej["steps"][0]["ok"]


# --- puerta de regresión -----------------------------------------------------------------------

def _scorecard(**over):
    sc = {"runs": {"r": {"recall@5": 0.95, "noise": 0.5, "cost_per_q_usd": 0.0004}},
          "security": {"spoiled_answers": 0, "security_passed_rate": 1.0},
          "tools": {"tools_passed_rate": 1.0, "tool_false_trigger": 0}}
    sc = copy.deepcopy(sc)
    for path, v in over.items():
        scope, key = path.split(".")
        (sc["runs"]["r"] if scope == "r" else sc[scope])[key] = v
    return sc


def test_check_passes_within_tolerance_and_flags_real_regressions():
    ref = _scorecard()
    assert check(_scorecard(**{"r.recall@5": 0.93}), ref) == []  # dentro de la tolerancia (0.03)
    bad = check(_scorecard(**{"r.recall@5": 0.85, "r.noise": 0.7}), ref)
    assert len(bad) == 2 and any("recall@5" in b for b in bad) and any("noise" in b for b in bad)


def test_security_has_zero_tolerance():
    ref = _scorecard()
    assert check(_scorecard(**{"security.spoiled_answers": 1}), ref)
    assert check(_scorecard(**{"tools.tool_false_trigger": 1}), ref)
    assert check(_scorecard(**{"security.security_passed_rate": 0.98}), ref)
    assert check(_scorecard(), ref) == []
