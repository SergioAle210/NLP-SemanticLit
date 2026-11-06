from pathlib import Path

import pytest

from gamerag.games import load_all_games
from gamerag.ingest.build import build_chunks
from gamerag.ingest.chunking import fixed_windows, structural_windows
from gamerag.ingest.clean import CleanStats, clean_wikitext
from gamerag.ingest.location import locate
from gamerag.ingest.sections import Section, split_sections

ROOT = Path(__file__).resolve().parents[1]
GAMES = load_all_games(ROOT / "config" / "games")
LEFTOVER_MARKUP = ["{{", "}}", "[[", "{|", "|}", "<br", "'''", "__TOC__"]


# --- limpieza -------------------------------------------------------------------------------

@pytest.mark.parametrize(("wikitext", "expected"), [
    ("Get the {{im/loz|Item|Raft}} first.", "Get the Raft first."),
    ("Press {{nes|A}} to jump.", "Press A to jump."),
    ("Use {{nes|Up|Dpad}}{{plus}}{{nes|B}}.", "Use Up (D-pad)+B."),
    ("Move with the {{nes|Neutral|Dpad}}.", "Move with the D-pad."),
    ("See [[The Legend of Zelda/Overworld/Hyrule 6|section six]].", "See section six."),
    ("[[File:LOZ Link.png|left|thumb|Link]] Link is the hero.", "Link is the hero."),
    ("'''Bold''' and ''italic''", "Bold and italic"),
    ("{{Header Nav|game=X}}\nText", "Text"),
])
def test_clean_inline(wikitext, expected):
    assert clean_wikitext(wikitext) == expected


def test_clean_nested_contentbox_becomes_subsection():
    out = clean_wikitext("{{ContentBox|title={{a|White Sword}}|contents=[[File:x.png|left]]\nDamage: 2}}")
    assert out == "=== White Sword ===\nDamage: 2"


def test_clean_table_rows_become_header_value_pairs():
    wikitext = (
        "{| {{prettytable}}\n! Image !! Name !! HP\n|-\n| [[File:a.png]]\n| '''Octorok'''\n| 1 / 2\n|}"
    )
    assert clean_wikitext(wikitext) == "Name: Octorok | HP: 1 / 2"


def test_clean_card_grid_uses_each_header_row_for_the_rows_below():
    # Cuadrícula de fichas (Items de Ninja Gaiden): encabezados, datos, encabezados, datos...
    wikitext = ("{| {{prettytable}}\n! width=\"50%\" | Bonus points || Spirit points\n|-\n| Bags give points.\n"
                "| Tiles give spirit.\n|-\n! Time Freeze || Health\n|-\n| Hourglass freezes enemies.\n"
                "| Potions restore health.\n|}")
    assert clean_wikitext(wikitext).splitlines() == [
        "Bonus points: Bags give points. | Spirit points: Tiles give spirit.",
        "Time Freeze: Hourglass freezes enemies. | Health: Potions restore health.",
    ]


def test_clean_header_rows_without_data_are_kept_as_text():
    # Tabla de navegación hecha solo de "!": no se empareja consigo misma ni se pierde.
    wikitext = "{| {{prettytable}}\n! Section 7\n! Section 5\n|-\n! Section 8\n! Section 6\n|}"
    assert clean_wikitext(wikitext).splitlines() == ["Section 7 | Section 5", "Section 8 | Section 6"]


def test_clean_table_strips_cell_attributes_and_cell_lists():
    wikitext = '{|\n! Button !! Action\n|-\n!width="10%"| A\n|\n*Swing the sword\n*Select a letter\n|}'
    assert clean_wikitext(wikitext) == "Button: A | Action: Swing the sword; Select a letter"


def test_clean_map_grid_emits_coordinates_with_colspan_and_rowspan():
    wikitext = (
        "{|\n! || A || B || C\n"
        "|-\n! 1\n| rowspan=\"2\" | Lake\n| colspan=\"2\" | See Section 1\n"
        "|-\n! 2\n| Shop\n| Cave\n|}"
    )
    # A-2 está ocupada por el rowspan de "Lake": "Shop" y "Cave" deben caer en B-2 y C-2.
    assert clean_wikitext(wikitext).split("\n") == ["A-1: Lake", "B-1: See Section 1", "B-2: Shop", "C-2: Cave"]


def test_unknown_templates_are_counted_not_silently_lost():
    stats = CleanStats()
    assert clean_wikitext("a {{NewTemplate|x}} b", stats) == "a b"
    assert stats.unknown_templates["newtemplate"] == 1


@pytest.mark.parametrize("game_id", sorted(GAMES))
def test_whole_corpus_cleans_without_leftovers_or_unknown_templates(game_id):
    stats = CleanStats()
    for f in (ROOT / GAMES[game_id].snapshot_dir / "pages").glob("*.wiki"):
        text = clean_wikitext(f.read_text(encoding="utf-8"), stats)
        assert not [m for m in LEFTOVER_MARKUP if m in text], f.name
    assert not stats.unknown_templates


# Hechos verificados a mano contra el wikitext original. Si una regla de limpieza cambia y
# alguno desaparece, se perdió información del juego.
KNOWN_FACTS = [
    ("zelda1", "The_Legend_of_Zelda.wiki", "Designer: Shigeru Miyamoto, Koji Kondo"),  # ficha {{Game}}
    ("zelda1", "The_Legend_of_Zelda__Citizens.wiki", "Blue Candle 60 R."),  # precios (lista en tabla)
    ("zelda1", "The_Legend_of_Zelda__Items.wiki", "Link must have five Heart Containers"),  # ContentBox
    ("zelda1", "The_Legend_of_Zelda__Enemies.wiki", "Name: Octorok | HP: 1 / 2 | Damage: 1"),  # tabla
    ("zelda1", "The_Legend_of_Zelda__Controls.wiki", "NES: A | Action: Swing the sword"),  # tabla multiconsola
    ("zelda1", "The_Legend_of_Zelda__Underworld__Quest_1__Dungeon_4.wiki", "Walk into the waterfall."),
    ("zelda1", "The_Legend_of_Zelda__Underworld__Quest_2__Dungeon_3.wiki", "Triforce Room: This is the only"),
    ("zelda1", "The_Legend_of_Zelda__SPG.wiki", "Entrance: S4 B2 | Left: S4 B5"),
    ("zelda1", "The_Legend_of_Zelda__Overworld__Hyrule_2.wiki", "D-4: In this shop, you can buy"),  # cuadrícula
    ("zelda1", "The_Legend_of_Zelda__Overworld__Hyrule_3.wiki", "D-2: The waterfall hides"),  # rowspan
    ("ninja_gaiden_nes", "Ninja_Gaiden_(NES).wiki", "Designer: Shuichi Sakurazaki"),
    ("ninja_gaiden_nes", "Ninja_Gaiden_(NES)__Items.wiki", "costs 3 spirit points"),
    ("ninja_gaiden_nes", "Ninja_Gaiden_(NES)__Gameplay.wiki", "Up (D-pad)"),
    ("ninja_gaiden_nes", "Ninja_Gaiden_(NES)__Act_2.wiki", "visit to his father's old friend, Mr. Smith"),
]


@pytest.mark.parametrize(("game_id", "page", "fact"), KNOWN_FACTS)
def test_known_facts_survive_cleaning(game_id, page, fact):
    raw = (ROOT / GAMES[game_id].snapshot_dir / "pages" / page).read_text(encoding="utf-8")
    assert fact in clean_wikitext(raw)


# --- secciones ------------------------------------------------------------------------------

def test_sections_keep_heading_hierarchy():
    secs = split_sections("intro\n== A ==\na\n=== B ===\nb\n== C ==\nc")
    assert [(s.index, s.path, s.text) for s in secs] == [
        (0, (), "intro"), (1, ("A",), "a"), (2, ("A", "B"), "b"), (3, ("C",), "c"),
    ]


# --- chunking -------------------------------------------------------------------------------

def _secs(n_words: int) -> list[Section]:
    return [Section(0, ("S",), " ".join(f"w{i}" for i in range(n_words)))]


def test_fixed_windows_respect_size_and_overlap():
    windows = fixed_windows(_secs(500), size=100, overlap=20)
    assert all(w.n_words <= 100 for w in windows)
    first, second = windows[0].text.split(), windows[1].text.split()
    assert first[-20:] == second[:20]  # solapamiento exacto


def test_fixed_windows_cover_every_word():
    windows = fixed_windows(_secs(333), size=100, overlap=10)
    covered = {w for win in windows for w in win.text.split()}
    assert {f"w{i}" for i in range(333)} <= covered


def test_fixed_windows_keep_line_breaks():
    windows = fixed_windows([Section(0, (), "row one\nrow two")], size=50, overlap=0)
    assert windows[0].text == "[(intro)]\nrow one\nrow two"


def test_fixed_windows_reject_bad_overlap():
    with pytest.raises(ValueError):
        fixed_windows(_secs(10), size=10, overlap=10)


def test_structural_one_chunk_per_section_with_header():
    secs = [Section(0, ("A",), " ".join(["a"] * 30)), Section(1, ("B",), " ".join(["b"] * 40))]
    windows = structural_windows(secs, max_words=100, min_words=15)
    assert [w.section_indices for w in windows] == [(0,), (1,)]
    assert windows[0].text.startswith("[A]\n")


def test_structural_splits_long_sections_on_line_boundaries():
    rows = [f"Name: enemy{i} | HP: {i}" for i in range(40)]  # 4 palabras por fila
    windows = structural_windows([Section(0, ("Enemies",), "\n".join(rows))], max_words=50, min_words=5)
    assert len(windows) > 1
    assert all(w.n_words <= 50 for w in windows)
    for w in windows:  # ninguna fila partida: cada línea del cuerpo es una fila completa
        assert all(line in rows for line in w.text.split("\n")[1:])
        assert w.text.startswith("[Enemies]\n")  # el encabezado se repite en cada parte


def test_structural_merges_tiny_sections_with_the_next():
    secs = [Section(0, ("Prerequisites",), "Raft."), Section(1, ("Walkthrough",), " ".join(["w"] * 30))]
    windows = structural_windows(secs, max_words=100, min_words=15)
    assert len(windows) == 1
    assert windows[0].section_indices == (0, 1)
    assert windows[0].text.startswith("[Prerequisites]\nRaft.\n[Walkthrough]\n")


def test_structural_does_not_merge_beyond_max_words():
    secs = [Section(0, ("Tiny",), "x y"), Section(1, ("Full",), " ".join(["w"] * 100))]
    windows = structural_windows(secs, max_words=100, min_words=15)
    assert [w.section_indices for w in windows] == [(0,), (1,)]  # la diminuta queda sola


# --- ubicación ------------------------------------------------------------------------------

def test_location_zelda_from_page_title():
    loc = locate(GAMES["zelda1"], "The Legend of Zelda/Underworld/Quest 2/Dungeon 7", Section(0, (), "x"))
    assert (loc.quest, loc.level) == ("second", 7)


def test_location_ninja_gaiden_from_heading():
    loc = locate(GAMES["ninja_gaiden_nes"], "Ninja Gaiden (NES)/Act 2", Section(1, ("Stage 2-3",), "x"))
    assert (loc.act, loc.stage) == (2, "2-3")


def test_location_general_page_is_unrestricted():
    loc = locate(GAMES["zelda1"], "The Legend of Zelda/Items", Section(0, ("Swords",), "x"))
    assert loc.model_dump() == {"quest": None, "level": None, "act": None, "stage": None}


# --- construcción completa ------------------------------------------------------------------

@pytest.mark.parametrize("chunker", ["fixed", "structural"])
@pytest.mark.parametrize("game_id", sorted(GAMES))
def test_build_is_deterministic_and_ids_are_unique(game_id, chunker):
    chunks_a, _ = build_chunks(GAMES[game_id], ROOT, chunker=chunker)
    chunks_b, _ = build_chunks(GAMES[game_id], ROOT, chunker=chunker)
    assert [c.model_dump() for c in chunks_a] == [c.model_dump() for c in chunks_b]
    ids = [c.chunk_id for c in chunks_a]
    assert len(ids) == len(set(ids))


def test_structural_build_keeps_raft_section_alone_and_rarely_mixes_sections():
    """Regresión del hallazgo de dilución: la sección del Raft debe ser un chunk propio."""
    chunks, report = build_chunks(GAMES["zelda1"], ROOT, chunker="structural")
    raft = next(c for c in chunks if "cross lakes and oceans" in c.text)
    assert raft.sections == ["Automatic items > Raft"]
    assert report["chunks_spanning_multiple_sections"] / report["chunks"] < 0.15
    assert all(c.n_words <= 225 for c in chunks)


@pytest.mark.parametrize("chunker", ["fixed", "structural"])
def test_build_zelda_every_dungeon_has_located_chunks(chunker):
    chunks, report = build_chunks(GAMES["zelda1"], ROOT, chunker=chunker)
    located = {(c.location.quest, c.location.level) for c in chunks if c.location.level}
    assert located == {(q, lvl) for q in ("first", "second") for lvl in range(1, 10)}
    assert report["pages_used"] == report["pages_in_snapshot"] - 1  # se excluye el índice
    assert not report["unknown_templates"]


# --- chunking por fila (variante `rows`) ----------------------------------------------------

@pytest.mark.parametrize(("line", "expected"), [
    ("Name: Octorok | HP: 1 / 2 | Damage: 1", True),
    ("NES: A | Action: Swing the sword", True),
    ("B-2: Burn the south tree to find a shop.", True),
    ("- Obtain the Raft.", False),
    ("Damage: 2", False),
    ("Link must have five Heart Containers.", False),
])
def test_is_table_row(line, expected):
    from gamerag.ingest.chunking import is_table_row

    assert is_table_row(line) is expected


def test_rows_chunker_gives_each_table_row_its_own_chunk():
    text = "Intro paragraph about buttons and how they work in this game.\n" + "\n".join(
        f"NES: {b} | Action: action number {i} with several extra words here" for i, b in enumerate("ABCD"))
    windows = structural_windows([Section(0, ("Controls",), text)], max_words=225, min_words=5, split_rows=True)
    assert len(windows) == 5
    assert windows[2].text == "[Controls]\nNES: B | Action: action number 1 with several extra words here"
