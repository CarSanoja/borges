from __future__ import annotations

import pytest

from borges.llm.client import LLMError
from borges.llm.json_output import parse_model, schema_instructions
from tests.llm.fakes import Answer


def test_schema_instructions_embeds_schema() -> None:
    text = schema_instructions(Answer)
    assert '"value"' in text
    assert "only a single JSON object" in text


def test_plain_json() -> None:
    assert parse_model('{"value": 3}', Answer) == Answer(value=3)


def test_think_block_removed() -> None:
    raw = '<think>maybe {"value": 99}</think>\n{"value": 4}'
    assert parse_model(raw, Answer).value == 4


def test_unclosed_opening_think_removed() -> None:
    assert parse_model('reasoning {"value": 1} more</think>{"value": 5}', Answer).value == 5


def test_fence_removed() -> None:
    assert parse_model('Here:\n```json\n{"value": 6, "label": "a"}\n```', Answer).label == "a"


def test_first_balanced_object_with_braces_in_strings() -> None:
    raw = 'prefix {"value": 7, "label": "}{"} trailing {"value": 8}'
    parsed = parse_model(raw, Answer)
    assert (parsed.value, parsed.label) == (7, "}{")


def test_no_object() -> None:
    with pytest.raises(LLMError, match="no JSON object"):
        parse_model("nothing here", Answer)


def test_invalid_json() -> None:
    with pytest.raises(LLMError, match="invalid JSON"):
        parse_model('{"value": 1,}', Answer)


def test_schema_violation() -> None:
    with pytest.raises(LLMError, match="value"):
        parse_model('{"value": "abc"}', Answer)


def test_fence_inside_json_string_value() -> None:
    text = '{"value": 1, "label": "```python\\nimport pandas\\n```"}'
    parsed = parse_model(text, Answer)
    assert parsed.value == 1 and "import pandas" in parsed.label


def test_fenced_object_after_prose_with_braces() -> None:
    text = 'Use {value} here.\n```json\n{"value": 4}\n```'
    assert parse_model(text, Answer).value == 4
