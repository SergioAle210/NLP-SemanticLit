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


def test_run_budget_is_per_process_not_forever(tmp_path):
    """El tope por corrida solo cuenta el gasto de este cliente; un proceso nuevo con la misma etiqueta no hereda
    el gasto anterior (si no, `serve` quedaba bloqueado para siempre). El tope total sigue siendo acumulado."""
    import time

    from gamerag.llm import Ledger

    ledger = Ledger(tmp_path / "u.sqlite3")
    ledger.record(run="serve", model="m", usage={"input_tokens": 1}, cost=0.9, cached=False)
    assert ledger.spent("serve") == 0.9
    assert ledger.spent("serve", since=time.time() + 1) == 0.0
    assert ledger.spent() == 0.9


def test_two_clients_share_one_budget_and_keep_request_telemetry_isolated(tmp_path):
    import time
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from gamerag.llm import Ledger
    from gamerag.telemetry import request_scope

    ready = Barrier(2)
    requests = []

    def create(**payload):
        requests.append(payload)
        time.sleep(0.05)  # el segundo solicitante llega mientras la primera llamada sigue en vuelo
        return SimpleNamespace(usage=SimpleNamespace(input_tokens=0, output_tokens=1))

    settings = Settings(_env_file=None, root=tmp_path, llm_cache=False, llm_price_input=0,
                        llm_price_output=1_000_000, llm_budget_usd=1.5, llm_run_budget_usd=1.5)
    api = SimpleNamespace(messages=SimpleNamespace(create=create))
    clients = [LLMClient(settings, client=api, ledger=Ledger(tmp_path / "usage.sqlite3")),
               LLMClient(settings, client=api, ledger=Ledger(tmp_path / "alias/../usage.sqlite3"))]
    assert clients[0].ledger.budget_lock is clients[1].ledger.budget_lock

    def request(index):
        with request_scope() as capture:
            ready.wait(timeout=5)
            try:
                clients[index].complete(MSG, max_tokens=1, run=f"request-{index}")
                status = "ok"
            except BudgetExceeded:
                status = "blocked"
            return status, capture.calls

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(request, range(2)))
    assert sorted(status for status, _ in results) == ["blocked", "ok"]
    assert len(requests) == 1 and clients[0].ledger.spent() == 1.0
    for index, (status, calls) in enumerate(results):
        assert len(calls) == 1 and calls[0]["run"] == f"request-{index}"
        assert calls[0]["status"] == ("ok" if status == "ok" else "error")
        if status == "blocked":
            assert calls[0]["error_type"] == "BudgetExceeded" and not calls[0]["usage_known"]


def test_ledger_connection_is_closed_after_operations(tmp_path):
    from gamerag.llm import Ledger

    path = tmp_path / "usage.sqlite3"
    ledger = Ledger(path)
    ledger.record(run="test", model="fake", usage={}, cost=0, cached=False)
    assert ledger.spent() == 0
    path.unlink()  # Windows rechaza la eliminación si una conexión conserva el archivo abierto.
    assert not path.exists()
