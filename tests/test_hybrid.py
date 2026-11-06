"""Tests de la fusión híbrida (RRF) y, si está instalado el extra `semantic`, del índice denso."""

import importlib.util
from pathlib import Path

import pytest

from gamerag.ingest.models import Chunk
from gamerag.retrieval.bm25 import BM25Index, Hit
from gamerag.retrieval.hybrid import RRF_K, HybridRetriever, rrf_fuse

HAS_SEMANTIC = importlib.util.find_spec("sentence_transformers") is not None
semantic = pytest.mark.skipif(not HAS_SEMANTIC, reason="requiere el extra `semantic`")


def _chunk(cid: str, text: str = "x", **loc) -> Chunk:
    return Chunk(chunk_id=cid, text=text, source="Game/Page", page=0, version="revid:1", url="u", section="s",
                 sections=["s"], hash=f"h-{cid}-{text}", chunker="test", n_words=len(text.split()), game="g",
                 location=loc)


def _ranking(*ids: str) -> list[Hit]:
    return [Hit(rank=r, score=1.0 / r, chunk=_chunk(cid)) for r, cid in enumerate(ids, 1)]


# --- RRF ------------------------------------------------------------------------------------

def test_rrf_scores_follow_formula():
    fused = rrf_fuse([_ranking("a", "b"), _ranking("b", "c")])
    scores = {h.chunk.chunk_id: h.score for h in fused}
    assert scores["b"] == pytest.approx(1 / (RRF_K + 2) + 1 / (RRF_K + 1))
    assert scores["a"] == pytest.approx(1 / (RRF_K + 1))
    assert scores["c"] == pytest.approx(1 / (RRF_K + 2))


def test_rrf_rewards_agreement_between_rankings():
    # "b" no es primero en ninguno, pero aparece alto en los dos -> gana.
    fused = rrf_fuse([_ranking("a", "b", "c"), _ranking("d", "b", "e")])
    assert fused[0].chunk.chunk_id == "b"
    assert [h.rank for h in fused] == list(range(1, len(fused) + 1))


def test_rrf_ties_are_deterministic_and_top_n_truncates():
    fused = rrf_fuse([_ranking("a"), _ranking("b")], top_n=1)
    assert [h.chunk.chunk_id for h in fused] == ["a"]  # empate: gana el primero visto


def test_rrf_ignores_raw_score_scales():
    big = [Hit(1, 999.0, _chunk("a")), Hit(2, 998.0, _chunk("b"))]
    small = [Hit(1, 0.01, _chunk("b")), Hit(2, 0.001, _chunk("a"))]
    fused = rrf_fuse([big, small])
    assert fused[0].score == pytest.approx(fused[1].score)  # solo importan las posiciones


def test_hybrid_retriever_fuses_bm25_rankings():
    # Corpus con el término en una minoría de documentos (con "raft" en la mayoría, el IDF de BM25 es negativo).
    chunks = [_chunk("a", "raft crosses water"), _chunk("b", "sword"), _chunk("c", "raft dock"),
              _chunk("d", "candle"), _chunk("e", "bombs"), _chunk("f", "ladder")]
    hybrid = HybridRetriever([BM25Index(chunks), BM25Index(list(reversed(chunks)))], candidates=3)
    hits = hybrid.search("raft", k=2)
    assert {h.chunk.chunk_id for h in hits} == {"a", "c"}


def test_hybrid_top_results_do_not_depend_on_requested_k():
    """Regresión: pedir más resultados (como hace el pipeline, k=50) no debe cambiar el orden de los
    primeros; la profundidad de la fusión es fija."""
    words = ["raft", "sword", "candle", "bombs", "ladder", "key", "ring", "shield", "arrow", "bow"]
    chunks = [_chunk(f"c{i}", " ".join(words[: (i % 10) + 1])) for i in range(30)]
    a, b = BM25Index(chunks), BM25Index(list(reversed(chunks)))
    hybrid = HybridRetriever([a, b], candidates=5)
    top5 = [h.chunk.chunk_id for h in hybrid.search("raft bow", k=5)]
    assert [h.chunk.chunk_id for h in hybrid.search("raft bow", k=50)][:5] == top5


# --- índice denso (requiere el extra `semantic`) --------------------------------------------

@semantic
def test_served_pipeline_matches_evaluated_recall():
    """Lo que sirve el pipeline (50 candidatos, filtros, top-5) debe tener el mismo Recall@5 que la
    configuración evaluada (ADR-0009: 0.89). Detectó que la fusión dependía de k (0.83 servido)."""
    from gamerag.evaluation.cases import is_relevant, load_cases
    from gamerag.evaluation.retrieval import RETRIEVAL_CATEGORIES
    from gamerag.pipeline import build_pipeline
    from gamerag.progress.models import Profile
    from gamerag.settings import Settings

    root = Path(__file__).resolve().parents[1]
    if not (root / "data" / "processed" / "zelda1" / "chunks.structural.jsonl").exists():
        pytest.skip("requiere la ingesta estructural de zelda1")
    pipe = build_pipeline(Settings(root=root))
    by_id = {c.chunk_id: c for c in pipe.retrievers["zelda1"].retrievers[0].chunks}
    cases = [c for c in load_cases(root / "eval" / "cases.jsonl")
             if c.game == "zelda1" and c.answerable and c.category in RETRIEVAL_CATEGORIES]
    prof = Profile(user_id="completionist", role="completionist")
    hits = sum(any(is_relevant(c, by_id[cid]) for cid in pipe.ask(c.question, "zelda1", prof)[1].context)
               for c in cases)
    assert hits / len(cases) >= 0.88

@semantic
def test_dense_index_finds_paraphrase_and_reuses_persisted_index(tmp_path: Path):
    from gamerag.retrieval.dense import DenseIndex
    from gamerag.retrieval.embeddings import get_embedder

    root = Path(__file__).resolve().parents[1]
    embedder = get_embedder("bge-small-en", str(root / "models"))
    chunks = [
        _chunk("raft", "The raft allows Link to cross lakes and oceans from a dock.", quest="first", level=3),
        _chunk("sword", "The white sword deals twice the damage of the wooden sword."),
        _chunk("candle", "Candles burn bushes and light up dark rooms."),
    ]
    idx = DenseIndex(chunks, embedder, tmp_path)
    assert idx.rebuilt
    hits = idx.search("How can I sail across the sea?", k=3)
    assert hits[0].chunk.chunk_id == "raft"
    assert all(-1.0 <= h.score <= 1.0 for h in hits)
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)

    # Metadatos de ubicación disponibles para pre-filtrar (gates).
    assert [h.chunk.chunk_id for h in idx.search("raft", k=3, where={"level": 3})] == ["raft"]

    # Mismos chunks y modelo -> reutiliza el índice persistido; si cambian, reconstruye.
    assert not DenseIndex(chunks, embedder, tmp_path).rebuilt
    assert DenseIndex(chunks[:2], embedder, tmp_path).rebuilt
