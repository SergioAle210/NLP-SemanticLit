"""HaikuGenerator con un cliente falso (sin red): citas verificadas, abstención, degradación."""

import json
from types import SimpleNamespace

from gamerag.generation.base import FallbackGenerator
from gamerag.generation.haiku import HaikuGenerator
from gamerag.llm import LLMClient
from gamerag.retrieval.bm25 import Hit
from gamerag.settings import Settings


def _hit(cid: str, text: str, rank: int = 1) -> Hit:
    chunk = SimpleNamespace(chunk_id=cid, source="Page", page=0, section="S", text=text)
    return Hit(chunk=chunk, score=1.0, rank=rank)


class FakeMessages:
    def __init__(self, payload):
        self.payload, self.calls, self.last = payload, 0, None

    def create(self, **kw):
        from anthropic.types import Message

        self.calls, self.last = self.calls + 1, kw
        text = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return Message.model_validate({
            "id": "m", "type": "message", "role": "assistant", "model": kw["model"],
            "content": [{"type": "text", "text": text}], "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 500, "output_tokens": 50},
        })


def make(tmp_path, payload):
    s = Settings(root=tmp_path, _env_file=None)
    api = SimpleNamespace(messages=FakeMessages(payload))
    return HaikuGenerator(LLMClient(s, client=api)), api


CTX = [_hit("a", "The boomerang is in the first dungeon."), _hit("b", "Other text.", 2)]


def test_valid_answer_keeps_only_context_citations(tmp_path):
    g, api = make(tmp_path, {"answer": "In dungeon 1.", "used_chunk_ids": ["a", "zzz"], "abstained": False})
    ans = g.generate("where is the boomerang?", CTX, game="zelda1", trace_id="t")
    assert not ans.abstained and [s.chunk_id for s in ans.sources] == ["a"]
    assert "temperature" not in api.messages.last  # los modelos 5.x lo rechazan


def test_answer_without_valid_citations_abstains(tmp_path):
    g, _ = make(tmp_path, {"answer": "Made up.", "used_chunk_ids": ["nope"], "abstained": False})
    assert g.generate("q", CTX, game="zelda1", trace_id="t").abstained


def test_model_abstention_is_respected(tmp_path):
    g, _ = make(tmp_path, {"answer": "idk", "used_chunk_ids": ["a"], "abstained": True})
    assert g.generate("q", CTX, game="zelda1", trace_id="t").abstained


def test_empty_context_makes_no_call(tmp_path):
    g, api = make(tmp_path, {})
    assert g.generate("q", [], game="zelda1", trace_id="t").abstained
    assert api.messages.calls == 0


def test_invalid_json_degrades_to_extractive(tmp_path):
    g, _ = make(tmp_path, "not json")
    ans = FallbackGenerator(g).generate("q", CTX, game="zelda1", trace_id="t")
    assert ans.needs_human_review and not ans.abstained
