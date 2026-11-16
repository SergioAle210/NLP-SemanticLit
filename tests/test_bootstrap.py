"""Preparación local, sin red, modelos ni llamadas al proveedor."""

import json
from pathlib import Path

import pytest
import yaml

from gamerag.bootstrap import ensure_corpora
from gamerag.settings import Settings


def _snapshot(root, name, title, text):
    directory = root / name
    directory.mkdir()
    (directory / "page.wiki").write_text(text, encoding="utf-8")
    (directory / "manifest.json").write_text(json.dumps({"pages": [
        {"title": title, "url": "https://example.test/page", "revid": 1, "file": "page.wiki"},
    ]}), encoding="utf-8")


@pytest.fixture()
def deployment(tmp_path):
    _snapshot(tmp_path, "primary", "Game/Dungeon 1", "== Start ==\nA long enough paragraph about safe controls.")
    _snapshot(tmp_path, "extra", "Fan Game", "== Gameplay ==\nAnother paragraph describing public game controls.")
    config = {"game_id": "g", "title": "Game", "platform": "NES", "year": 1990,
              "snapshot_dir": "primary", "progress_model": "level_set", "levels": [1, 2], "quests": ["first"],
              "location_from_title": r"Dungeon (?P<level>\d)", "tools": ["search_documents"],
              "extra_sources": [{"site": "fan", "snapshot_dir": "extra", "general_headings": "Gameplay"}]}
    (tmp_path / "configs").mkdir()
    config_path = tmp_path / "configs/g.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    settings = Settings(_env_file=None, root=tmp_path, data_dir=Path("custom-data"),
                        games_config_dir=Path("configs"), only_games=["g"],
                        profile="full", ANTHROPIC_API_KEY="not-a-real-key")
    return settings, config_path


def test_effective_full_builds_both_corpora_then_reuses_verified_outputs(deployment):
    settings, _ = deployment
    built = ensure_corpora(settings)
    assert [(r.tag, r.status) for r in built] == [("structural", "built"), ("structural-multi", "built")]
    assert all(Path(r.path).is_relative_to(settings.root / "custom-data") for r in built)
    assert not (settings.root / "data").exists()
    assert all(r.status == "reused" for r in ensure_corpora(settings))
    Path(built[0].path).write_text("corrupt\n", encoding="utf-8")
    repaired = ensure_corpora(settings)
    assert [r.status for r in repaired] == ["built", "reused"]
    assert json.loads(Path(repaired[0].path).read_text(encoding="utf-8").splitlines()[0])["game"] == "g"


def test_secondary_snapshot_and_permission_config_invalidate_fingerprints(deployment):
    settings, config_path = deployment
    first = ensure_corpora(settings)
    (settings.root / "extra/page.wiki").write_text("== Gameplay ==\nUpdated controls in the second source.",
                                                   encoding="utf-8")
    changed = ensure_corpora(settings)
    assert [r.status for r in changed] == ["reused", "built"]
    assert changed[1].fingerprint != first[1].fingerprint
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["extra_sources"][0]["general_headings"] = "Reception"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    assert all(r.status == "built" for r in ensure_corpora(settings))


def test_blank_full_key_prepares_only_primary_and_unknown_game_is_rejected(deployment):
    settings, _ = deployment
    offline = Settings(_env_file=None, root=settings.root, games_config_dir=settings.games_config_dir,
                       data_dir=settings.data_dir, profile="full", ANTHROPIC_API_KEY=" ")
    assert [result.tag for result in ensure_corpora(offline)] == ["structural"]
    offline.only_games = ["unknown"]
    with pytest.raises(ValueError, match="juegos desconocidos"):
        ensure_corpora(offline)
