"""Perfil de configuracion `full`: preset evaluado, solo con clave de API y sin pisar lo fijado a mano."""

import pytest
from pydantic import ValidationError

from gamerag.settings import Settings


def _s(**kw):
    return Settings(_env_file=None, **kw)


def test_base_profile_is_offline_and_free():
    s = _s()
    assert s.profile == "base" and s.generator == "extractive" and not s.use_graph and not s.secondary_search


def test_full_profile_without_api_key_stays_base():
    s = _s(profile="full", anthropic_api_key=None)
    assert s.generator == "extractive" and not s.use_graph


def test_full_profile_with_key_enables_the_evaluated_stack():
    s = _s(profile="full", ANTHROPIC_API_KEY="sk-test")
    assert (s.generator, s.use_graph, s.evidence_eval, s.secondary_search, s.secondary_mode, s.secondary_k) == \
        ("haiku", True, True, True, "mixed", 5)
    assert s.evidence_mode == "on_abstain" and s.spoiler_gates and s.security_guards


def test_explicit_fields_win_over_the_preset():
    s = _s(profile="full", ANTHROPIC_API_KEY="sk-test", generator="extractive", secondary_k=3)
    assert s.generator == "extractive" and s.secondary_k == 3 and s.use_graph


def test_invalid_profile_is_rejected():
    with pytest.raises(ValidationError):
        _s(profile="turbo")


@pytest.mark.parametrize("key", ["", "  ", "\t\n"])
def test_blank_key_does_not_activate_full(key):
    settings = _s(profile="full", ANTHROPIC_API_KEY=key)
    assert settings.anthropic_api_key is None
    assert settings.generator == "extractive" and not settings.use_graph and not settings.secondary_search


def test_example_env_allows_full_preset_and_explicit_overrides(tmp_path):
    from pathlib import Path

    example = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text(example.replace("GAMERAG_PROFILE=base", "GAMERAG_PROFILE=full")
                       .replace("ANTHROPIC_API_KEY=", "ANTHROPIC_API_KEY=not-a-real-key"), encoding="utf-8")
    full = Settings(_env_file=env_file)
    assert full.generator == "haiku" and full.use_graph and full.evidence_eval
    assert full.secondary_search and full.secondary_mode == "mixed" and full.secondary_k == 5
    override = Settings(_env_file=env_file, generator="extractive", secondary_search=False)
    assert override.generator == "extractive" and not override.secondary_search and override.use_graph
