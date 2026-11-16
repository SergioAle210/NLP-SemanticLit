"""Regresiones de evidencia exacta, observabilidad concurrente y metadatos persistidos."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import httpx
import pytest
from anthropic import APIConnectionError
from anthropic.types import Message

from gamerag.games import load_all_games
from gamerag.generation.base import ExtractiveGenerator, FallbackGenerator
from gamerag.graph import graph_from
from gamerag.guardrails.content import ContentPolicy
from gamerag.ingest.build import build_chunks
from gamerag.ingest.models import Chunk
from gamerag.llm import LLMClient
from gamerag.pipeline import Pipeline, Trace
from gamerag.progress.models import LevelSetProgress, Profile
from gamerag.retrieval.bm25 import Hit
from gamerag.schemas import Answer
from gamerag.settings import Settings
from gamerag.store import Store
from gamerag.telemetry import current_capture, record_call, request_scope


def chunk(text="A permitted passage", **over):
    return Chunk(**{
        "chunk_id": "g:manual:0", "text": text, "source": "Manual", "page": 3, "version": "fixture:1",
        "url": "https://example.org/manual", "section": "Training", "sections": ["Training"],
        "hash": hashlib.sha256(text.encode()).hexdigest(), "chunker": "test", "n_words": len(text.split()),
        "game": "g", **over,
    })


class Retriever:
    def __init__(self, document):
        self.document = document

    def search(self, query, k=5):
        return [Hit(1, 1.0, self.document)]


def test_concurrent_requests_keep_calls_answer_and_evidence_isolated():
    barrier = Barrier(2)

    class Generator(ExtractiveGenerator):
        def generate(self, question, context, **kw):
            record_call(model=question, status="ok", input_tokens=len(question))
            barrier.wait(timeout=10)
            return super().generate(question, context, **kw)

    pipe = Pipeline({"g": Retriever(chunk())}, generator=Generator())
    profile = Profile(user_id="p", role="completionist")
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda q: pipe.ask(q, "g", profile), ["first", "second"]))
    for (answer, trace), question in zip(results, ["first", "second"], strict=True):
        assert [c["model"] for c in trace.llm_calls] == [question]
        assert trace.final_answer == answer
        assert trace.final_evidence[0].text == "A permitted passage"
        assert trace.llm_calls[0]["stage"] == "generation"
    assert results[0][1].trace_id != results[1][1].trace_id
    assert current_capture() is None


def test_secondary_generation_keeps_exact_context_and_previous_attempts():
    from gamerag.agents.evidence import Verdict

    class Generator(ExtractiveGenerator):
        def generate(self, question, context, **kw):
            if context[0].chunk.origin == "strategywiki":
                return Answer(answer="Insufficient", abstained=True, **kw)
            return super().generate(question, context, **kw)

    primary = chunk("Primary partial clue")
    secondary = chunk("Exact secondary solution", chunk_id="g:secondary:0", origin="other", page=7)
    pipe = Pipeline({"g": Retriever(primary)}, generator=Generator(),
                    secondary={"g": Retriever(secondary)}, secondary_replace=True)
    evidence = SimpleNamespace(evaluate=lambda q, ctx: Verdict(False, "missing", "new query"))
    graph = graph_from(pipe, evidence=evidence)
    answer, trace = graph.ask("question", "g", Profile(user_id="p", role="completionist"))
    assert not answer.abstained
    assert trace.final_evidence[0].text == secondary.text
    assert trace.final_evidence[0].page == 7
    assert trace.context == [secondary.chunk_id]
    assert {c.chunk_id for c in trace.candidates} == {primary.chunk_id, secondary.chunk_id}
    calls = [s for s in trace.stages if s["name"] == "generation"]
    assert len(calls) == 2
    assert trace.latency_ms["generation"] >= sum(s["duration_ms"] for s in calls) - 0.03


@pytest.mark.parametrize("use_secondary", [False, True], ids=["primary", "secondary"])
def test_real_overworld_answer_and_evidence_hide_locked_routes(use_secondary):
    from gamerag.agents.evidence import Verdict

    root = Path(__file__).resolve().parents[1]
    games = load_all_games(root / "config/games")
    corpus, _ = build_chunks(games["zelda1"], root, chunker="structural")
    original = next(c for c in corpus if c.chunk_id == "zelda1:overworld-hyrule-3:001")
    assert "White Sword" in original.text and "fifth dungeon" in original.text
    probe = chunk("An incomplete clue", game="zelda1", chunk_id="zelda1:probe:0")

    class Generator(ExtractiveGenerator):
        def generate(self, question, context, **kw):
            if context and context[0].chunk.chunk_id == probe.chunk_id:
                return Answer(answer="Insufficient evidence", abstained=True, **kw)
            return super().generate(question, context, **kw)

    pipe = Pipeline(
        {"zelda1": Retriever(probe if use_secondary else original)},
        generator=Generator(max_chars=10000), content_policy=ContentPolicy(games),
        secondary={"zelda1": Retriever(original)} if use_secondary else None,
        secondary_replace=True,
    )
    if use_secondary:
        evaluator = SimpleNamespace(evaluate=lambda q, ctx: Verdict(False, "missing", "White Sword"))
        pipe = graph_from(pipe, evidence=evaluator)
    novice = Profile(user_id="novato", role="player", progress={
        "zelda1": LevelSetProgress(quest="first", completed_levels=[1], current_level=2),
    })
    question = "What is the white sword?"
    answer, trace = pipe.ask(question, "zelda1", novice)

    assert not answer.abstained and trace.final_answer == answer
    assert len(trace.final_evidence) == 1
    evidence = trace.final_evidence[0]
    for text in (answer.answer, evidence.text):
        assert "White Sword" in text and "5 Heart Containers" in text
        assert "fifth dungeon" not in text and "Lost Hills" not in text
        assert "E-1:" not in text and "D-2:" not in text and "E-2:" not in text
    assert evidence.is_excerpt and evidence.source_hash == original.hash
    assert evidence.evidence_hash == hashlib.sha256(evidence.text.encode()).hexdigest()
    for field in ("chunk_id", "source", "page"):
        assert getattr(evidence, field) == getattr(answer.sources[0], field) == getattr(original, field)

    if not use_secondary:
        results, search_trace = pipe.search(question, "zelda1", novice)
        assert results[0].chunk.text == evidence.text == search_trace.final_evidence[0].text
    complete, complete_trace = pipe.ask(question, "zelda1", Profile(user_id="full", role="completionist"))
    assert "fifth dungeon" in complete.answer
    assert complete_trace.final_evidence[0].text == original.text
    assert original.text != evidence.text  # Per-request projection must not mutate the shared corpus.


def test_http_retry_cache_and_fallback_are_recorded_separately(tmp_path, monkeypatch):
    monkeypatch.setattr("gamerag.llm.time.sleep", lambda _: None)
    attempts = []

    def create(**kw):
        attempts.append(kw)
        if len(attempts) == 1:
            raise APIConnectionError(request=httpx.Request("POST", "https://example.org"))
        return Message.model_validate({
            "id": "m", "type": "message", "role": "assistant", "model": "test",
            "content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 12, "output_tokens": 4},
        })

    llm = LLMClient(Settings(root=tmp_path, _env_file=None),
                    client=SimpleNamespace(messages=SimpleNamespace(create=create)))
    with request_scope() as capture:
        llm.complete([{"role": "user", "content": "same"}])
        llm.complete([{"role": "user", "content": "same"}])
    assert [c["status"] for c in capture.calls] == ["error", "ok", "cache_hit"]
    assert [c["attempt"] for c in capture.calls] == [1, 2, 0]
    assert capture.calls[0]["usage_known"] is False
    assert capture.calls[1]["input_tokens"] == 12
    assert capture.calls[2]["cost_usd"] == 0
    assert len(attempts) == 2

    class Broken:
        name = "broken"

        def generate(self, *a, **kw):
            raise ValueError("secret must not be logged")

    pipe = Pipeline({"g": Retriever(chunk())}, generator=FallbackGenerator(Broken()))
    answer, trace = pipe.ask("question", "g", Profile(user_id="p", role="completionist"))
    assert answer.needs_human_review
    assert trace.degradations[0]["error_type"] == "ValueError"
    assert "secret must not" not in trace.model_dump_json()


def test_audit_redacts_nested_context_and_answer(tmp_path):
    pipe = Pipeline({"g": Retriever(chunk("Contact ana@example.org for help", version="revid:1234567890",
                                          hash="sha256:123456789abcdef"))})
    _, trace = pipe.ask("help", "g", Profile(user_id="p", role="completionist"))
    store = Store(tmp_path / "audit.sqlite3")
    store.log_trace(trace)
    saved = store.recent_traces()[0]
    assert "ana@example.org" not in str(saved)
    assert "[EMAIL]" in saved["final_evidence"][0]["text"]
    assert "[EMAIL]" in saved["final_answer"]["answer"]
    evidence = saved["final_evidence"][0]
    assert evidence["version"] == "revid:1234567890"
    assert evidence["source_hash"] == "sha256:123456789abcdef"
    assert evidence["evidence_hash"] == trace.final_evidence[0].evidence_hash
    assert evidence["audit_redacted"]
    assert evidence["recorded_text_hash"] == hashlib.sha256(evidence["text"].encode()).hexdigest()
    store.close()


def test_metadata_only_change_rebuilds_persistent_index(tmp_path):
    pytest.importorskip("chromadb")
    import numpy as np

    from gamerag.retrieval.dense import DenseIndex

    class Embedder:
        model = SimpleNamespace(key="fixture")

        def embed_passages(self, texts):
            return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)

        def embed_query(self, text):
            return np.array([1.0, 0.0], dtype=np.float32)

    first = chunk(location={"level": 1}, version="fixture:1")
    idx = DenseIndex([first], Embedder(), tmp_path)
    assert idx.search("query", where={"level": 1})
    second = first.model_copy(update={"version": "fixture:2",
                                      "location": first.location.model_copy(update={"level": 9})})
    idx = DenseIndex([second], Embedder(), tmp_path)
    assert idx.rebuilt
    assert idx.search("query", where={"level": 1}) == []
    hits = idx.search("query", where={"version": "fixture:2"})
    assert hits[0].chunk.location.level == 9
    assert not DenseIndex([second], Embedder(), tmp_path).rebuilt


def test_shared_audit_store_persists_every_concurrent_request(tmp_path):
    store = Store(tmp_path / "concurrent.sqlite3")

    def save(i):
        store.log_trace(Trace(trace_id=str(i), question="question", game="g", user_id="p", role="player",
                              retriever="test", generator="test"))

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(save, range(100)))
    assert len(store.all_traces()) == 100
    assert {t["trace_id"] for t in store.all_traces()} == {str(i) for i in range(100)}
    store.close()
