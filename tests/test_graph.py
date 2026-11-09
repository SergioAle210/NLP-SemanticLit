"""El grafo de estados (LangGraph) se comporta igual que el Pipeline lineal y registra su recorrido."""

import pytest

from gamerag.graph import GraphPipeline, graph_from
from gamerag.guardrails.base import GameFilter, GuardResult
from gamerag.ingest.models import Chunk
from gamerag.pipeline import Pipeline
from gamerag.progress.models import LevelSetProgress, Profile
from gamerag.retrieval.bm25 import BM25Index
from gamerag.schemas import Answer


def _chunk(cid: str, text: str, **loc) -> Chunk:
    return Chunk(chunk_id=cid, text=text, source=f"Zelda/{cid}", page=0, version="revid:1", url="u",
                 section="s", sections=["s"], hash=f"h-{cid}", chunker="test", n_words=len(text.split()),
                 game="zelda1", location=loc)


CORPUS = [
    _chunk("raft", "The raft crosses lakes and oceans from a dock.", level=3, quest="first"),
    _chunk("sword", "The white sword needs five heart containers."),
    _chunk("ladder", "The ladder crosses small gaps.", level=4, quest="first"),
]
PLAYER = Profile(user_id="p", role="player",
                 progress={"zelda1": LevelSetProgress(quest="first", completed_levels=[1], current_level=2)})


class _LevelGate:
    name = "g2_location"

    def allows(self, chunk, profile, game):
        prog = profile.progress.get(game)
        if profile.unrestricted or chunk.location.level is None or prog is None:
            return True
        return chunk.location.level in {*prog.completed_levels, prog.current_level}


class _Reject:
    name = "always_reject"

    def check(self, answer, context, profile):
        return GuardResult(False, "test")


def _pair(**kw):
    lin = Pipeline({"zelda1": BM25Index(CORPUS)}, top_k=2, candidates=5, **kw)
    return lin, graph_from(lin)


def _norm(answer, trace):
    a = answer.model_dump(exclude={"trace_id"})
    t = trace.model_dump(exclude={"trace_id", "latency_ms"})
    return a, t, sorted(trace.latency_ms)


SCENARIOS = [
    ("answered", "white sword hearts", {}, "answered"),
    ("rejected_input", "   ", {}, "rejected_input"),
    ("blocked_by_access", "raft ladder", {"access_filters": [_LevelGate()]}, "blocked_by_access"),
    ("rejected_output", "sword", {"output_guards": [_Reject()]}, "rejected_output"),
    ("abstained", "zzzz qqqq", {}, "abstained"),
]


@pytest.mark.parametrize(("name", "question", "kw", "outcome"), SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_graph_matches_linear_pipeline(name, question, kw, outcome):
    lin, graph = _pair(**kw)
    expected = _norm(*lin.ask(question, "zelda1", PLAYER))
    got = _norm(*graph.ask(question, "zelda1", PLAYER))
    assert got == expected
    assert got[1]["outcome"] == outcome


def test_graph_records_the_visited_nodes():
    _, graph = _pair()
    assert isinstance(graph, GraphPipeline)
    steps = lambda q, **_: graph.run(q, "zelda1", PLAYER)["steps"]  # noqa: E731
    assert steps("white sword hearts") == ["input", "route", "retrieve", "generate", "guard"]
    assert steps("   ") == ["input"]


def test_graph_short_circuits_when_blocked_by_access():
    lin = Pipeline({"zelda1": BM25Index(CORPUS)}, access_filters=[GameFilter(), _LevelGate()], candidates=5)
    state = graph_from(lin).run("raft ladder", "zelda1", PLAYER)
    assert state["steps"] == ["input", "route", "retrieve"]  # nunca llega al generador
    assert state["answer"].blocked_by_spoiler


# --- evaluador de evidencia con reintento acotado ---------------------------------------------------

from gamerag.agents.evidence import EvidenceEvaluator, Verdict  # noqa: E402


class _Eval:
    """Evaluador falso: veredictos en orden; registra qué contexto vio."""

    def __init__(self, *verdicts):
        self.verdicts, self.calls = list(verdicts), 0

    def evaluate(self, question, context):
        self.calls += 1
        return self.verdicts.pop(0) if self.verdicts else Verdict(True)


def _ev_graph(ev, **kw):
    lin = Pipeline({"zelda1": BM25Index(CORPUS)}, top_k=2, candidates=5)
    return graph_from(lin, evidence=ev, **{"evidence_mode": "always", **kw})


def test_insufficient_evidence_rewrites_and_retries_once():
    ev = _Eval(Verdict(False, "off-topic", "white sword hearts"), Verdict(True))
    state = _ev_graph(ev).run("zzzz qqqq", "zelda1", PLAYER)
    assert state["steps"] == ["input", "route", "retrieve", "evaluate", "rewrite", "retrieve", "evaluate",
                              "generate", "guard"]
    assert state["attempts"] == 1 and state["query"] == "white sword hearts"
    assert [e["sufficient"] for e in state["trace"].evidence] == [False, True]


def test_retries_are_bounded_by_max_rewrites():
    always_bad = _Eval(*[Verdict(False, "bad", "other query")] * 5)
    state = _ev_graph(always_bad, max_rewrites=1).run("white sword", "zelda1", PLAYER)
    assert always_bad.calls == 2 and state["attempts"] == 1
    assert state["steps"][-2:] == ["generate", "guard"]  # tras agotar reintentos, genera igual


def test_no_evaluator_means_same_steps_as_before():
    state = _ev_graph(None).run("white sword hearts", "zelda1", PLAYER)
    assert "evaluate" not in state["steps"]


def test_evaluator_fails_open(tmp_path):
    from types import SimpleNamespace

    from gamerag.llm import LLMClient
    from gamerag.settings import Settings

    class Boom:
        def create(self, **kw):
            raise TimeoutError("down")

    llm = LLMClient(Settings(root=tmp_path, _env_file=None), client=SimpleNamespace(messages=Boom()))
    hits = BM25Index(CORPUS).search("sword", k=2)
    assert EvidenceEvaluator(llm).evaluate("sword?", hits).sufficient


# --- modo condicional: solo interviene si el generador se abstiene ---------------------------------

class _AbstainFirst:
    """Generador falso: se abstiene la primera vez y responde con el contexto la segunda."""

    name = "abstain-first"

    def __init__(self):
        self.calls = 0

    def generate(self, question, context, *, game, trace_id):
        from gamerag.generation.base import ExtractiveGenerator

        self.calls += 1
        if self.calls == 1:
            return Answer(answer="no", abstained=True, game=game, trace_id=trace_id)
        return ExtractiveGenerator().generate(question, context, game=game, trace_id=trace_id)


def _cond(ev, gen=None, **kw):
    lin = Pipeline({"zelda1": BM25Index(CORPUS)}, top_k=2, candidates=5, generator=gen)
    return graph_from(lin, evidence=ev, **kw)


def test_on_abstain_costs_nothing_when_the_generator_answers():
    ev = _Eval()
    state = _cond(ev).run("white sword hearts", "zelda1", PLAYER)
    assert ev.calls == 0 and state["steps"] == ["input", "route", "retrieve", "generate", "guard"]


def test_on_abstain_rewrites_and_regenerates():
    ev, gen = _Eval(Verdict(False, "miss", "white sword hearts")), _AbstainFirst()
    state = _cond(ev, gen).run("zzzz", "zelda1", PLAYER)
    assert state["steps"] == ["input", "route", "retrieve", "generate", "evaluate", "rewrite", "retrieve",
                              "generate", "guard"]
    assert gen.calls == 2 and not state["answer"].abstained


def test_on_abstain_keeps_abstention_when_evidence_is_judged_sufficient():
    ev, gen = _Eval(Verdict(True, "docs ok")), _AbstainFirst()
    state = _cond(ev, gen).run("white sword hearts", "zelda1", PLAYER)
    assert state["steps"][-3:] == ["generate", "evaluate", "guard"] and state["answer"].abstained
    assert gen.calls == 1
