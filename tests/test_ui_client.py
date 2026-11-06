"""Tests del cliente HTTP del frontend contra la API real (en memoria, pipeline BM25 liviano).

No requieren Streamlit: `TestClient` de FastAPI es un `httpx.Client`, así que el cliente lo usa tal cual.
"""

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from gamerag.api import create_app
from gamerag.ingest.models import Chunk
from gamerag.pipeline import Pipeline
from gamerag.retrieval.bm25 import BM25Index
from gamerag.settings import Settings
from gamerag.store import Store
from gamerag.ui.client import ApiClient, ApiError, audit_row, describe_progress, hit_label

ROOT = Path(__file__).resolve().parents[1]


def _chunk(cid: str, text: str) -> Chunk:
    return Chunk(chunk_id=cid, text=text, source=f"Zelda/{cid}", page=0, version="revid:1", url=f"https://x/{cid}",
                 section="s", sections=["s"], hash=f"h-{cid}", chunker="test", n_words=len(text.split()),
                 game="zelda1")


@pytest.fixture()
def api(tmp_path):
    settings = Settings(root=ROOT, state_db=tmp_path / "ui.sqlite3")
    store = Store(settings.state_db)
    # 4 fragmentos: con 2, el IDF de BM25 queda <= 0 y no recupera nada.
    corpus = [_chunk("raft", "The raft crosses lakes and oceans from a dock."),
              _chunk("sword", "The white sword needs five heart containers."),
              _chunk("candle", "The blue candle burns bushes."),
              _chunk("bombs", "Bombs open hidden passages.")]
    pipeline = Pipeline({"zelda1": BM25Index(corpus)}, top_k=2, candidates=5, retriever_name="bm25/test")
    with TestClient(create_app(settings=settings, pipeline=pipeline, store=store)) as c:
        yield ApiClient(base_url="http://testserver", client=c)
    store.close()


def test_catalog(api):
    assert api.health()["status"] == "ok"
    assert [g["game_id"] for g in api.games() if g["available"]] == ["zelda1"]
    assert "admin" in {p["user_id"] for p in api.profiles()}


def test_ask_and_search_return_the_same_context(api):
    ans = api.ask("How do I cross the oceans?", "zelda1", "novato")
    ctx = api.search("How do I cross the oceans?", "zelda1", "novato")
    assert ans["answer"]["sources"][0]["chunk_id"] == "raft"
    # La interfaz muestra el texto del contexto con /search: debe ser el mismo que usó /ask.
    assert [h["chunk_id"] for h in ctx["hits"]] == ans["trace"]["context"]


def test_errors_become_api_error(api):
    with pytest.raises(ApiError) as e:
        api.ask("raft", "mario", "novato")
    assert e.value.status == 404 and "mario" in e.value.detail
    with pytest.raises(ApiError) as e:
        api.audit("novato")
    assert e.value.status == 403


def test_unreachable_api_is_reported():
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)
    c = ApiClient(base_url="http://nope", client=httpx.Client(transport=httpx.MockTransport(refuse),
                                                              base_url="http://nope"))
    with pytest.raises(ApiError) as e:
        c.health()
    assert e.value.status == 0 and "http://nope" in e.value.detail


def test_audit_rows_are_flat(api):
    api.ask("raft", "zelda1", "novato")
    rows = [audit_row(r) for r in api.audit("admin")]
    assert rows[0]["usuario"] == "novato" and rows[0]["resultado"] == "answered"
    assert all(not isinstance(v, (dict, list)) for v in rows[0].values())


def test_hit_label_distinguishes_parts_of_the_same_section():
    a = {"source": "The Legend of Zelda/Walkthrough", "section": "1st Quest Overview",
         "chunk_id": "zelda1:walkthrough:002",
         "text": "[1st Quest Overview]\n- Obtain the letter from the old man in section one and then show it"}
    b = dict(a, chunk_id="zelda1:walkthrough:003", text="[1st Quest Overview]\n- Locate and enter level 5")
    la, lb = hit_label(a), hit_label(b)
    assert la != lb
    assert la.startswith("Walkthrough › 1st Quest Overview · walkthrough:002")
    assert "[1st Quest Overview]" not in la and "Obtain the letter" in la and la.endswith("…”")
    assert lb.endswith("“- Locate and enter level 5”")


def test_describe_progress():
    novato = {"role": "player", "progress": {"zelda1": {"kind": "level_set", "quest": "first",
                                                        "completed_levels": [1], "current_level": 2},
                                             "ninja_gaiden_nes": {"kind": "linear_stage", "current_stage": "1-2"}}}
    assert "niveles completados: 1" in describe_progress(novato, "zelda1")
    assert "1-2" in describe_progress(novato, "ninja_gaiden_nes")
    assert "sin restricciones" in describe_progress({"role": "admin"}, "zelda1")
