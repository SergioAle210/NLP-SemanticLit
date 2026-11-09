import json
import re
from pathlib import Path

import pytest

from gamerag.games import GameConfig, ProgressModel, load_all_games

ROOT = Path(__file__).resolve().parents[1]
GAMES = load_all_games(ROOT / "config" / "games")


def test_all_games_load():
    assert set(GAMES) == {"zelda1", "ninja_gaiden_nes", "gta_sa", "oot", "ac2", "doom", "rdr1"}
    assert GAMES["zelda1"].progress_model is ProgressModel.LEVEL_SET
    assert GAMES["oot"].progress_model is ProgressModel.LEVEL_SET
    for g in ("ninja_gaiden_nes", "gta_sa", "ac2", "doom", "rdr1"):
        assert GAMES[g].progress_model is ProgressModel.LINEAR_STAGE


def test_every_extra_source_has_a_snapshot_with_license():
    for cfg in GAMES.values():
        for extra in cfg.extra_sources:
            manifest = json.loads((ROOT / extra.snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
            assert manifest["license"], (cfg.game_id, extra.site)
            assert manifest["pages"], (cfg.game_id, extra.site)


@pytest.mark.parametrize("game_id", ["zelda1", "ninja_gaiden_nes"])
def test_snapshot_exists_and_matches_manifest(game_id):
    snap = ROOT / GAMES[game_id].snapshot_dir
    manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["license"]["name"].startswith("Creative Commons Attribution-ShareAlike")
    for page in manifest["pages"]:
        assert (snap / page["file"]).is_file(), page["file"]
        assert page["revid"], page["title"]


def test_zelda_title_regex_finds_all_18_dungeons():
    cfg = GAMES["zelda1"]
    snap = ROOT / cfg.snapshot_dir
    titles = [p["title"] for p in json.loads((snap / "manifest.json").read_text("utf-8"))["pages"]]
    found = {(m["quest"], m["level"]) for t in titles if (m := re.search(cfg.location_from_title, t))}
    assert found == {(q, str(lvl)) for q in "12" for lvl in range(1, 10)}


def test_ninja_gaiden_heading_regex_matches_configured_stages():
    """Cada etapa configurada aparece como encabezado en el snapshot, y viceversa."""
    cfg = GAMES["ninja_gaiden_nes"]
    pages = (ROOT / cfg.snapshot_dir / "pages").glob("*Act_*.wiki")
    headings = set()
    for p in pages:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("==") and (m := re.search(cfg.location_from_heading, line)):
                headings.add(m["stage"])
    assert headings == set(cfg.stages)
    assert cfg.stage_index("1-1") < cfg.stage_index("6-5")


def test_graph_tool_rejected_for_linear_game():
    data = GAMES["ninja_gaiden_nes"].model_dump()
    data["tools"] = [*data["tools"], "next_available_levels"]
    with pytest.raises(ValueError, match="next_available_levels"):
        GameConfig.model_validate(data)


def test_zelda_franchise_wikis_are_scoped_out_of_the_secondary_tier():
    games = load_all_games(ROOT / "config" / "games")
    for game in ("zelda1", "oot"):
        scopes = {s.site: s.scope for s in games[game].extra_sources}
        assert scopes["zeldapedia"] == scopes["zeldawiki"] == "franchise"
    assert all(s.scope == "game" for g in ("gta_sa", "ac2", "doom", "rdr1", "ninja_gaiden_nes")
               for s in games[g].extra_sources)
