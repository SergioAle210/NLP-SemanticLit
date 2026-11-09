"""Control de costo del LLM: tope total, tope por corrida, caché y modo sin conexión (sin red)."""

from types import SimpleNamespace

import pytest

from gamerag.llm import BudgetExceeded, CacheMiss, LLMClient
from gamerag.settings import Settings


class FakeMessages:
    def __init__(self):
        self.calls = 0

    def create(self, **kw):
        from anthropic.types import Message

        self.calls += 1
        return Message.model_validate({
            "id": "msg_1", "type": "message", "role": "assistant", "model": kw["model"],
            "content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1000, "output_tokens": 100},
        })


def make(tmp_path, **over):
    over = {"llm_price_input": 1.0, "llm_price_output": 5.0, **over}
    s = Settings(root=tmp_path, _env_file=None, **over)
    api = SimpleNamespace(messages=FakeMessages())
    return LLMClient(s, client=api), api


MSG = [{"role": "user", "content": "hello"}]


def test_cost_is_recorded(tmp_path):
    c, _ = make(tmp_path)
    msg = c.complete(MSG, max_tokens=50)
    assert c.text(msg) == "ok"
    # 1000 * $1/M + 100 * $5/M = $0.0015
    assert c.ledger.spent() == pytest.approx(0.0015)


def test_repeat_is_served_from_cache_for_free(tmp_path):
    c, api = make(tmp_path)
    c.complete(MSG, max_tokens=50)
    c.complete(MSG, max_tokens=50)
    assert api.messages.calls == 1
    assert c.ledger.spent() == pytest.approx(0.0015)
    assert c.ledger.summary()["cache_hits"] == 1


def test_total_budget_blocks_before_calling(tmp_path):
    c, api = make(tmp_path, llm_budget_usd=0.0001)
    with pytest.raises(BudgetExceeded):
        c.complete(MSG, max_tokens=500)
    assert api.messages.calls == 0


def test_run_budget_is_independent(tmp_path):
    c, api = make(tmp_path, llm_run_budget_usd=0.003)
    c.complete([{"role": "user", "content": "a"}], max_tokens=10, run="eval-1")
    c.complete([{"role": "user", "content": "b"}], max_tokens=10, run="eval-1")
    with pytest.raises(BudgetExceeded):  # 0.003 gastado: la tercera ya no cabe en 'eval-1'
        c.complete([{"role": "user", "content": "c"}], max_tokens=500, run="eval-1")
    c.complete([{"role": "user", "content": "c"}], max_tokens=10, run="eval-2")  # otra corrida: cabe


def test_offline_mode_never_calls_the_api(tmp_path):
    c, api = make(tmp_path, llm_offline=True)
    with pytest.raises(CacheMiss):
        c.complete(MSG, max_tokens=50)
    assert api.messages.calls == 0


def test_max_tokens_is_capped_by_settings(tmp_path):
    c, _ = make(tmp_path, llm_max_tokens=64)
    seen = {}
    orig = c._client.messages.create
    c._client.messages.create = lambda **kw: (seen.update(kw), orig(**kw))[1]
    c.complete(MSG, max_tokens=100_000)
    assert seen["max_tokens"] == 64
