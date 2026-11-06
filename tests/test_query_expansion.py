"""Tests de la transformación de consultas: corrección ortográfica, glosario y multi-consulta."""

from pathlib import Path

import pytest

from gamerag.games import QueryExpansionConfig, RewriteRule, load_all_games
from gamerag.ingest.models import Chunk
from gamerag.retrieval.bm25 import BM25Index, Hit
from gamerag.retrieval.query_expansion import ExpandingRetriever, QueryExpander, _edit_distance_le1

ROOT = Path(__file__).resolve().parents[1]


def _chunk(cid: str, text: str) -> Chunk:
    return Chunk(chunk_id=cid, text=text, source=f"Game/{cid}", page=0, version="revid:1", url="u", section="s",
                 sections=["s"], hash=f"h-{cid}", chunker="test", n_words=len(text.split()), game="g")


CORPUS = [
    _chunk("controls", "NES: A | Action: Swing the sword. NES: B | Action: Use subweapon."),
    _chunk("rupees", "Rupees are the currency. Collect rupees from enemies. Rupees buy items."),
    _chunk("bombs", "Bombs blast holes in weak walls. Bombs are sold in shops."),
    _chunk("enemies", "Enemies attack Link. Some enemies attack from far away."),
    _chunk("cross", "Use the ladder to cross rivers. The raft lets you cross lakes."),
]
CONFIG = QueryExpansionConfig(synonyms={"attack": ["swing the sword"], "money": ["rupees"], "heal": ["hearts"]})


@pytest.fixture()
def qx() -> QueryExpander:
    return QueryExpander(CONFIG, CORPUS)


@pytest.mark.parametrize(("a", "b", "expected"), [
    ("atack", "attack", True),   # inserción
    ("bombz", "bombs", True),    # sustitución
    ("swordd", "sword", True),   # borrado
    ("refilled", "refills", False),
    ("cost", "coast", True),     # distancia 1, pero se excluye por longitud en correct()
])
def test_edit_distance_le1(a, b, expected):
    assert _edit_distance_le1(a, b) is expected


@pytest.mark.parametrize(("query", "expected"), [
    ("how do i atack?", "how do i attack?"),       # typo corregido (attack aparece 2 veces)
    ("can i blow up walls with bombz?", "can i blow up walls with bombs?"),
    ("How can I sail across the sea?", "How can I sail across the sea?"),  # "across" no se vuelve "cross"
    ("How much does it cost?", "How much does it cost?"),  # palabras cortas no se tocan
    ("how can i heal?", "how can i heal?"),          # palabra del glosario: se expande, no se corrige
])
def test_correct_is_conservative(qx, query, expected):
    assert qx.correct(query) == expected


def test_rewrite_appends_glossary_terms_once(qx):
    assert qx.rewrite("How can I attack? attack!") == "How can I attack? attack! swing the sword"
    assert qx.rewrite("Where is the raft?") == "Where is the raft?"


def test_variants_keep_original_first(qx):
    assert qx.variants("how do i atack?") == ["how do i atack?", "how do i attack? swing the sword"]
    assert qx.variants("Where is the raft?") == ["Where is the raft?"]  # sin cambios: una sola variante


def test_rewrite_rules_apply_backreferences():
    cfg = QueryExpansionConfig(rewrites=[RewriteRule(match=r"\blevel[- ]?(\d)\b", replace=r"dungeon \1")])
    assert QueryExpander(cfg, CORPUS).rewrite("What is in Level-3?") == "What is in dungeon 3?"


def test_expanding_retriever_finds_vocabulary_mismatch(qx):
    base = BM25Index(CORPUS)
    # Sin expansión, "attack" lleva a los enemigos; con el glosario, aparecen los controles.
    assert base.search("How can I attack?", k=1)[0].chunk.chunk_id == "enemies"
    ids = [h.chunk.chunk_id for h in ExpandingRetriever(base, qx, candidates=5).search("How can I attack?", k=2)]
    assert "controls" in ids


def test_expanding_retriever_without_changes_delegates_to_base(qx):
    calls = []

    class _Spy:
        def search(self, query, k=5):
            calls.append(query)
            return [Hit(rank=1, score=1.0, chunk=CORPUS[0])]

    ExpandingRetriever(_Spy(), qx).search("Where is the raft?", k=3)
    assert calls == ["Where is the raft?"]


def test_zelda_glossary_has_no_identifier_rewrites():
    """Las reglas Level/Quest se descartaron por la ablación (docs/evaluation/results.md)."""
    cfg = load_all_games(ROOT / "config" / "games")["zelda1"].query_expansion
    assert cfg.rewrites == [] and "attack" in cfg.synonyms
