import re
from pathlib import Path

import pytest

from gamerag.evaluation.cases import EvalCase, is_relevant, load_cases
from gamerag.evaluation.metrics import coverage_at_k, mean, precision_at_k, recall_at_k, reciprocal_rank
from gamerag.evaluation.retrieval import COURSE_CATEGORIES, aggregate, evaluate_case
from gamerag.games import load_all_games
from gamerag.ingest.build import build_chunks
from gamerag.ingest.clean import clean_wikitext
from gamerag.ingest.models import Chunk, Location
from gamerag.ingest.sections import split_sections
from gamerag.retrieval.bm25 import BM25Index, index_text
from gamerag.retrieval.tokenize import tokenize

ROOT = Path(__file__).resolve().parents[1]
GAMES = load_all_games(ROOT / "config" / "games")
CASES = load_cases(ROOT / "eval" / "cases.jsonl")


def _chunk(cid: str, text: str, source: str = "Game/Page") -> Chunk:
    return Chunk(chunk_id=cid, text=text, source=source, page=0, version="revid:1", url="u", section="s",
                 sections=["s"], hash="h", chunker="test", n_words=len(text.split()), game="g")


@pytest.fixture(scope="module")
def zelda_chunks():
    chunks, _ = build_chunks(GAMES["zelda1"], ROOT)
    return chunks


# --- tokenización ---------------------------------------------------------------------------

def test_tokenize_keeps_identifiers_whole_and_split():
    assert tokenize("Level-4 at D-4", phrases=False) == ["level-4", "level", "4", "d-4", "d", "4"]
    assert tokenize("Level-4 at D-4") == ["level-4", "level", "4", "level_4", "d-4", "d", "4", "d_4"]


@pytest.mark.parametrize(("text", "phrase"), [
    ("how do i beat level 1?", "level_1"),
    ("Level-1", "level_1"),                      # misma forma con guion
    ("Underworld/Quest 1/Dungeon 3", "dungeon_3"),
    ("Underworld/Quest 1/Dungeon 3", "quest_1"),
    ("Stage 2-3", "stage_2-3"),                  # etapas de Ninja Gaiden
])
def test_tokenize_adds_word_number_phrases(text, phrase):
    assert phrase in tokenize(text)


def test_phrase_tokens_distinguish_dungeon_numbers():
    # Bolsa de palabras: "Quest 1/Dungeon 3" contiene "dungeon" y "1" igual que "Dungeon 1".
    assert "dungeon_1" not in tokenize("Underworld/Quest 1/Dungeon 3")
    assert "the_1" not in tokenize("the 1") and "level_" not in " ".join(tokenize("level one"))


def test_tokenize_drops_stopwords_and_possessives():
    assert tokenize("What is Link's sword?") == ["link", "sword"]


# --- BM25 -----------------------------------------------------------------------------------

def test_index_text_drops_game_name_from_title():
    c = _chunk("c", "body", source="The Legend of Zelda/Underworld/Quest 1/Dungeon 4")
    assert index_text(c) == "Underworld/Quest 1/Dungeon 4\nbody"


def test_index_text_adds_location_aliases():
    # La wiki dice "Quest 1/Dungeon 4"; el juego y los jugadores, "Level-4" y "first quest".
    c = _chunk("c", "body", source="The Legend of Zelda/Underworld/Quest 1/Dungeon 4")
    c = c.model_copy(update={"location": Location(quest="first", level=4)})
    assert index_text(c) == "Underworld/Quest 1/Dungeon 4\nLevel 4 · first quest\nbody"
    assert "level_4" in tokenize(index_text(c))


def test_bm25_ranks_exact_term_match_first():
    idx = BM25Index([_chunk("a", "the raft crosses water"), _chunk("b", "the sword cuts"), _chunk("c", "bombs")])
    hits = idx.search("raft", k=3)
    assert hits[0].chunk.chunk_id == "a" and hits[0].rank == 1


def test_bm25_returns_only_matching_chunks():
    """Regresión: un chunk sin términos de la consulta (score 0) no debe aparecer como candidato,
    porque contaminaría la fusión RRF de la búsqueda híbrida."""
    idx = BM25Index([_chunk("a", "raft water"), _chunk("b", "sword"), _chunk("c", "candle"), _chunk("d", "bombs")])
    assert [h.chunk.chunk_id for h in idx.search("raft", k=4)] == ["a"]
    assert idx.search("zzz", k=4) == []
    assert idx.search("the of", k=4) == []  # solo stopwords


def test_bm25_ties_keep_corpus_order():
    idx = BM25Index([_chunk("a", "raft x"), _chunk("b", "raft y"), _chunk("c", "sword"), _chunk("d", "bombs"),
                     _chunk("e", "candle")])
    assert [h.chunk.chunk_id for h in idx.search("raft", k=2)] == ["a", "b"]


# --- métricas (ejemplos de las diapositivas del curso, tema 08) -----------------------------

def test_recall_at_k_course_example():
    # 10 consultas, 8 con el chunk correcto en el top-5 -> Recall@5 = 0.80
    per_query = [[False, True]] * 8 + [[False] * 5] * 2
    assert mean([recall_at_k(r, 5) for r in per_query]) == pytest.approx(0.80)


def test_precision_at_k_course_example():
    assert precision_at_k([True, False, True, False, False], 5) == pytest.approx(0.40)


def test_mrr_course_example():
    ranks = [[True], [False, False, True], [False, False, False, False, True]]
    assert mean([reciprocal_rank(r) for r in ranks]) == pytest.approx((1 + 1 / 3 + 1 / 5) / 3)


def test_coverage_counts_evidence_parts():
    assert coverage_at_k([{0}, set(), {0}], n_parts=2, k=3) == 0.5
    assert coverage_at_k([{0}, {1}], n_parts=2, k=2) == 1.0


# --- banco de pruebas -----------------------------------------------------------------------

def test_cases_meet_course_distribution_for_zelda():
    zelda = [c for c in CASES if c.game == "zelda1"]
    counts = {cat: sum(c.category == cat for c in zelda) for cat in
              ("direct", "paraphrase", "exact_id", "compound", "ambiguous", "unanswerable", "version")}
    assert counts == {"direct": 5, "paraphrase": 3, "exact_id": 3, "compound": 3, "ambiguous": 2,
                      "unanswerable": 2, "version": 2}


@pytest.mark.parametrize("case", [c for c in CASES if c.answerable], ids=lambda c: c.id)
def test_expected_pages_contain_the_evidence(case: EvalCase):
    """Cada (fuente, sección) esperada contiene alguna parte de la evidencia."""
    snap = ROOT / GAMES[case.game].snapshot_dir
    files = {p.stem.replace("__", "/").replace("_", " "): p for p in (snap / "pages").glob("*.wiki")}
    norm = lambda t: re.sub(r"\s+", " ", t).lower()  # noqa: E731
    for source, page in zip(case.expected_sources, case.expected_pages, strict=True):
        sections = split_sections(clean_wikitext(files[source].read_text(encoding="utf-8")))
        text = norm(sections[page].text)
        assert any(norm(a) in text for alts in case.evidence for a in alts), (source, page)


@pytest.fixture(scope="module")
def zelda_structural_chunks():
    chunks, _ = build_chunks(GAMES["zelda1"], ROOT, chunker="structural")
    return chunks


@pytest.mark.parametrize("case", [c for c in CASES if c.answerable and c.game == "zelda1"], ids=lambda c: c.id)
def test_every_answerable_case_has_a_relevant_chunk(case, zelda_chunks, zelda_structural_chunks):
    """Si ningún chunk es relevante, el caso es imposible de recuperar (error del caso o de la ingesta).
    Se verifica con ambos chunkings: la comparación entre estrategias solo es válida si ambas pueden acertar."""
    assert any(is_relevant(case, c) for c in zelda_chunks)
    assert any(is_relevant(case, c) for c in zelda_structural_chunks)


def test_unanswerable_cases_have_no_supporting_text(zelda_chunks):
    corpus = " ".join(c.text.lower() for c in zelda_chunks)
    assert "hookshot" not in corpus and "horse" not in corpus


# --- regresión de la línea base -------------------------------------------------------------

def test_bm25_baseline_does_not_regress(zelda_chunks):
    """Línea base medida el 2026-11-05: Recall@5 = 0.78, MRR = 0.47 (docs/evaluation/results.md).
    Un cambio en limpieza, chunking o tokenización que la empeore debe ser intencional."""
    idx = BM25Index(zelda_chunks)
    cases = [c for c in CASES if c.game == "zelda1" and c.answerable and c.category in COURSE_CATEGORIES]
    report = aggregate([evaluate_case(c, idx.search(c.question, 20)) for c in cases])
    assert report["recall@5"] >= 0.77
    assert report["mrr"] >= 0.46
