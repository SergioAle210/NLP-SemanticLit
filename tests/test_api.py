"""Tests de la API (FastAPI) con un pipeline liviano (BM25) y una base SQLite temporal."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from gamerag.api import create_app
from gamerag.ingest.models import Chunk
from gamerag.pipeline import Pipeline
from gamerag.retrieval.bm25 import BM25Index
from gamerag.settings import Settings
from gamerag.store import Store, redact_pii

ROOT = Path(__file__).resolve().parents[1]


def _chunk(cid: str, text: str, game: str = "zelda1") -> Chunk:
    return Chunk(chunk_id=cid, text=text, source=f"Zelda/{cid}", page=0, version="revid:1", url=f"https://x/{cid}",
                 section="s", sections=["s"], hash=f"h-{cid}", chunker="test", n_words=len(text.split()), game=game)


CORPUS = [_chunk("raft", "The raft crosses lakes and oceans from a dock."),
          _chunk("sword", "The white sword needs five heart containers."),
          _chunk("candle", "The blue candle burns bushes."),
          _chunk("bombs", "Bombs open hidden passages.")]


@pytest.fixture()
def client(tmp_path):
    settings = Settings(root=ROOT, state_db=tmp_path / "test.sqlite3")
    store = Store(settings.state_db)
    pipeline = Pipeline({"zelda1": BM25Index(CORPUS)}, top_k=2, candidates=5, retriever_name="bm25/test")
    with TestClient(create_app(settings=settings, pipeline=pipeline, store=store)) as c:
        yield c
    store.close()


def test_health_and_games(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["games"] == ["zelda1"] and h["generator"] == "extractive"
    games = {g["game_id"]: g for g in client.get("/games").json()}
    assert games["zelda1"]["available"] and games["zelda1"]["quests"] == ["first", "second"]
    assert not games["ninja_gaiden_nes"]["available"] and len(games["ninja_gaiden_nes"]["stages"]) == 21


def test_profiles_are_seeded(client):
    ids = {p["user_id"] for p in client.get("/profiles").json()}
    assert ids == {"novato", "intermedio", "segunda_vuelta", "completionist", "admin"}
    assert client.get("/profiles/novato").json()["progress"]["zelda1"]["completed_levels"] == [1]
    assert client.get("/profiles/nadie").status_code == 404


def test_ask_returns_course_contract_and_trace(client):
    r = client.post("/ask", json={"question": "How do I cross the oceans?", "game": "zelda1", "user_id": "novato"})
    assert r.status_code == 200
    body = r.json()
    ans = body["answer"]
    assert {"answer", "sources", "abstained", "tool_used", "needs_human_review"} <= ans.keys()  # §11
    assert ans["sources"][0]["chunk_id"] == "raft" and not ans["abstained"]
    assert body["trace"]["trace_id"] == ans["trace_id"] and body["trace"]["outcome"] == "answered"


def test_ask_without_trace(client):
    r = client.post("/ask", json={"question": "raft", "game": "zelda1", "user_id": "novato", "include_trace": False})
    assert r.json()["trace"] is None


@pytest.mark.parametrize(("payload", "status"), [
    ({"question": "raft", "game": "mario", "user_id": "novato"}, 404),     # juego no disponible
    ({"question": "raft", "game": "zelda1", "user_id": "nadie"}, 404),     # perfil desconocido
    ({"question": "", "game": "zelda1", "user_id": "novato"}, 422),        # validación de entrada
    ({"question": "x" * 501, "game": "zelda1", "user_id": "novato"}, 422),
    ({"question": "raft", "game": "Zelda 1!", "user_id": "novato"}, 422),
])
def test_ask_validates_input(client, payload, status):
    assert client.post("/ask", json=payload).status_code == status


def test_search_returns_context_without_generating(client):
    body = client.post("/search", json={"question": "raft oceans", "game": "zelda1", "user_id": "novato"}).json()
    assert body["hits"][0]["chunk_id"] == "raft" and body["hits"][0]["url"] == "https://x/raft"
    assert body["trace"]["outcome"] == "retrieved" and "generation" not in body["trace"]["latency_ms"]


def test_audit_logs_redacted_questions_and_requires_admin(client):
    client.post("/ask", json={"question": "raft? mail me at link@hyrule.com", "game": "zelda1", "user_id": "novato"})
    assert client.get("/audit", params={"user_id": "novato"}).status_code == 403
    logs = client.get("/audit", params={"user_id": "admin"}).json()
    assert logs[0]["user_id"] == "novato" and "[EMAIL]" in logs[0]["question"]
    assert "link@hyrule.com" not in str(logs)


def test_reset_profiles_requires_admin(client):
    assert client.post("/admin/reset-profiles", params={"user_id": "novato"}).status_code == 403
    assert client.post("/admin/reset-profiles", params={"user_id": "admin"}).json() == {"reset": 5}


@pytest.mark.parametrize(("text", "expected"), [
    ("write to ana.perez@uvg.edu.gt", "write to [EMAIL]"),
    ("call +502 5555-1234 now", "call [PHONE] now"),
    ("my key is sk-ant-api03-abc_DEF-123", "my key is [SECRET]"),
    ("Which button swings the sword?", "Which button swings the sword?"),
])
def test_redact_pii(text, expected):
    assert redact_pii(text) == expected


def test_rate_limit_per_user(tmp_path):
    settings = Settings(root=ROOT, state_db=tmp_path / "rl.sqlite3", rate_limit_per_min=3)
    store = Store(settings.state_db)
    pipeline = Pipeline({"zelda1": BM25Index(CORPUS)}, top_k=2, candidates=5)
    body = {"question": "How do I cross the oceans?", "game": "zelda1", "user_id": "novato"}
    with TestClient(create_app(settings=settings, pipeline=pipeline, store=store)) as c:
        codes = [c.post("/ask", json=body).status_code for _ in range(4)]
        other = c.post("/ask", json={**body, "user_id": "intermedio"}).status_code
    store.close()
    assert codes == [200, 200, 200, 429] and other == 200
