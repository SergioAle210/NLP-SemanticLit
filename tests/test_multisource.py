"""Ingesta con varias wikis por juego: ids estables, procedencia y ubicación a prueba de fallos."""

import json
from pathlib import Path

from gamerag.games import ExtraSource, GameConfig
from gamerag.guardrails.location import LocationGate
from gamerag.ingest.build import build_chunks
from gamerag.progress.models import LevelSetProgress, Profile

PRIMARY_TEXT = "== Overview ==\n" + "The Forest Temple is the third dungeon. " * 12
FAN_TEXT = ("== Gameplay ==\n" + "You explore dungeons and fight bosses with many items. " * 12 +
            "\n== Plot ==\n" + "Ganondorf is defeated in the final castle at the very end. " * 12)


def _snapshot(root: Path, name: str, pages: dict[str, str]) -> Path:
    d = root / name
    (d / "pages").mkdir(parents=True)
    manifest = []
    for i, (title, text) in enumerate(pages.items()):
        (d / "pages" / f"p{i}.wiki").write_text(text, encoding="utf-8")
        manifest.append({"title": title, "url": f"http://x/{i}", "revid": 100 + i, "file": f"pages/p{i}.wiki",
                         "chars": len(text)})
    (d / "manifest.json").write_text(json.dumps({"pages": manifest}), encoding="utf-8")
    return Path(name)


def _cfg(tmp_path: Path, **extra) -> GameConfig:
    primary = _snapshot(tmp_path, "primary", {"Game/Dungeon 3": PRIMARY_TEXT})
    fan = _snapshot(tmp_path, "fan", {"Fan Page": FAN_TEXT})
    return GameConfig(game_id="g", title="Game", platform="NES", year=1990, snapshot_dir=primary,
                      progress_model="level_set", levels=[1, 2, 3], quests=["first"],
                      location_from_title=r"Dungeon (?P<level>\d)", tools=["search_documents"],
                      extra_sources=[ExtraSource(site="fandom", snapshot_dir=fan, **extra)])


def _by_source(chunks):
    return {c.source: c for c in reversed(chunks)}  # el primer chunk de cada fuente


def test_primary_ids_and_titles_are_unchanged_and_extras_are_namespaced(tmp_path):
    chunks, report = build_chunks(_cfg(tmp_path), tmp_path, chunker="structural", min_words=5, extras=True)
    primary = [c for c in chunks if c.source == "Game/Dungeon 3"]
    extra = [c for c in chunks if c.source.startswith("fandom: ")]
    assert primary and extra and all(c.chunk_id.startswith("g:dungeon-3:") for c in primary)
    assert all(c.chunk_id.startswith("g:fandom:fan-page:") for c in extra)
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    assert report["chunks_by_source"].keys() == {"strategywiki", "fandom"}


def test_unlocated_extra_content_is_restricted_by_default(tmp_path):
    chunks, report = build_chunks(_cfg(tmp_path), tmp_path, chunker="structural", min_words=5, extras=True)
    assert all(c.location.restricted for c in chunks if c.source.startswith("fandom: "))
    assert not any(c.location.restricted for c in chunks if c.source == "Game/Dungeon 3")
    assert report["chunks_restricted"] > 0


def test_general_headings_stay_visible_but_plot_stays_restricted(tmp_path):
    cfg = _cfg(tmp_path, general_headings="Gameplay")
    chunks, _ = build_chunks(cfg, tmp_path, chunker="structural", min_words=5, extras=True)
    fan = [c for c in chunks if c.source.startswith("fandom: ")]
    assert {c.section: c.location.restricted for c in fan} == {"Gameplay": False, "Plot": True}


def test_gate_hides_restricted_chunks_from_players_not_from_unrestricted(tmp_path):
    cfg = _cfg(tmp_path)
    chunks, _ = build_chunks(cfg, tmp_path, chunker="structural", min_words=5, extras=True)
    fan_chunk = next(c for c in chunks if c.source.startswith("fandom: "))
    gate = LocationGate({"g": cfg})
    player = Profile(user_id="p", role="player",
                     progress={"g": LevelSetProgress(quest="first", completed_levels=[1, 2], current_level=3)})
    assert not gate.allows(fan_chunk, player, "g")
    assert gate.allows(fan_chunk, Profile(user_id="c", role="completionist"), "g")
