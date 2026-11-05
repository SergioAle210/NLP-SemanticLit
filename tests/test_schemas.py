import pytest
from pydantic import ValidationError

from gamerag.schemas import Answer, Source


def _base(**kw):
    return {"answer": "x", "abstained": False, "game": "zelda1", "trace_id": "t1"} | kw


def test_grounded_answer_ok():
    a = Answer(**_base(sources=[Source(source="manual.pdf", page=4, chunk_id="18")]))
    assert a.sources[0].page == 4


def test_abstention_without_sources_ok():
    assert Answer(**_base(abstained=True)).abstained


def test_tool_answer_without_sources_ok():
    assert Answer(**_base(tool_used="query_game_facts")).tool_used


def test_ungrounded_answer_rejected():
    with pytest.raises(ValidationError, match="fuentes"):
        Answer(**_base())


def test_required_course_fields_present_in_json():
    dumped = Answer(**_base(abstained=True)).model_dump()
    assert {"answer", "sources", "abstained", "tool_used", "needs_human_review"} <= dumped.keys()
