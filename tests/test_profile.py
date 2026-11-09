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
