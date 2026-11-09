"""Segunda búsqueda en las wikis extra: solo se usa si la evidencia es insuficiente (sin red)."""

from gamerag.agents.evidence import Verdict
from gamerag.generation.base import ExtractiveGenerator
from gamerag.graph import graph_from
from gamerag.ingest.models import Chunk
from gamerag.pipeline import Pipeline
from gamerag.progress.models import Profile
from gamerag.retrieval.bm25 import BM25Index
from gamerag.schemas import Answer


def _chunk(cid, text, origin="strategywiki"):
    return Chunk(chunk_id=cid, text=text, source=f"{origin}: {cid}", page=0, version="r", url="u", section="s",
                 sections=["s"], hash=cid, chunker="t", n_words=len(text.split()), game="g", origin=origin)


PRIMARY = [_chunk("sword", "The white sword needs five heart containers.")]
EXTRA = [_chunk("lore", "The ancient ocarina melody opens the hidden temple door.", origin="fanwiki"),
         _chunk("filler1", "Bombs destroy cracked walls near the river.", origin="fanwiki"),
         _chunk("filler2", "Rupees are collected from defeated octoroks.", origin="fanwiki"),
         _chunk("filler3", "Keese bats fly erratically in dark rooms.", origin="fanwiki")]
CHIEF = Profile(user_id="c", role="completionist")


class _Eval:
    def __init__(self, *verdicts):
        self.verdicts, self.calls = list(verdicts), 0

    def evaluate(self, question, context):
        self.calls += 1
        return self.verdicts.pop(0) if self.verdicts else Verdict(True)


class _AbstainOnce:
    """Se abstiene si el contexto no contiene la palabra 'ocarina'; si no, responde con el extractivo."""

    name = "needs-ocarina"

    def generate(self, question, context, *, game, trace_id):
        if not any("ocarina" in h.chunk.text for h in context):
            return Answer(answer="no", abstained=True, game=game, trace_id=trace_id)
        return ExtractiveGenerator().generate(question, context, game=game, trace_id=trace_id)


def _graph(ev, secondary=True, mode="always"):
    base = Pipeline({"g": BM25Index(PRIMARY)}, top_k=2, candidates=5, generator=_AbstainOnce())
    sec = {"g": BM25Index(EXTRA)} if secondary else None
    return graph_from(base, evidence=ev, evidence_mode=mode, secondary=sec, secondary_k=2)


def test_secondary_search_adds_extra_wiki_chunks_when_evidence_is_insufficient():
    ev = _Eval(Verdict(False, "off-topic", "ocarina melody temple door"))
    state = _graph(ev).run("white sword hearts", "g", CHIEF)
    assert state["steps"] == ["input", "route", "retrieve", "evaluate", "secondary", "generate", "guard"]
    assert state["trace"].secondary == ["lore"] and "lore" in state["trace"].context
    assert not state["answer"].abstained and any(s.chunk_id == "lore" for s in state["answer"].sources)


def test_secondary_search_is_skipped_when_evidence_is_sufficient():
    ev = _Eval(Verdict(True))
    state = _graph(ev).run("white sword hearts", "g", CHIEF)
    assert "secondary" not in state["steps"] and state["trace"].secondary == []


def test_without_secondary_retrievers_the_flow_is_unchanged():
    ev = _Eval(Verdict(False, "bad", ""))
    state = _graph(ev, secondary=False).run("white sword hearts", "g", CHIEF)
    assert "secondary" not in state["steps"]


def test_secondary_search_happens_only_once():
    ev = _Eval(Verdict(False, "bad", "nothing relevant here"), Verdict(False, "bad", "still nothing"),
               Verdict(False, "bad", "again"))
    state = _graph(ev, mode="on_abstain").run("white sword hearts", "g", CHIEF)
    assert state["steps"].count("secondary") == 1


def test_secondary_chunks_still_go_through_the_access_gates():
    class _BlockExtra:
        name = "block_extra"

        def allows(self, chunk, profile, game):
            return chunk.origin == "strategywiki"

    ev = _Eval(Verdict(False, "off-topic", "ocarina melody temple door"))
    base = Pipeline({"g": BM25Index(PRIMARY)}, top_k=2, candidates=5, generator=_AbstainOnce(),
                    access_filters=[_BlockExtra()])
    g = graph_from(base, evidence=ev, evidence_mode="always", secondary={"g": BM25Index(EXTRA)}, secondary_k=2)
    state = g.run("white sword hearts", "g", CHIEF)
    assert state["trace"].secondary == [] and state["answer"].abstained


def test_mixed_mode_replaces_the_context_with_the_mixed_index():
    ev = _Eval(Verdict(False, "off-topic", "ocarina melody temple door"))
    base = Pipeline({"g": BM25Index(PRIMARY)}, top_k=2, candidates=5, generator=_AbstainOnce())
    g = graph_from(base, evidence=ev, evidence_mode="always", secondary={"g": BM25Index(PRIMARY + EXTRA)},
                   secondary_k=2, secondary_replace=True)
    state = g.run("white sword hearts", "g", CHIEF)
    assert state["trace"].context[0] == "lore" or "lore" in state["trace"].context
    assert "lore" in state["trace"].secondary and not state["answer"].abstained
