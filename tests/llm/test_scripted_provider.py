from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.llm.client import LLMClient, LLMError, Role
from borges.llm.scripted_provider import ScriptedLLM
from tests.llm.fakes import Answer


def write(directory: Path, name: str, record: dict) -> None:
    (directory / name).write_text(json.dumps(record))


async def test_replays_parsed_fixture(tmp_path: Path) -> None:
    write(
        tmp_path,
        "coder__s1.o1.json",
        {"model": "fx", "text": "", "parsed": {"value": 2}, "tokens_in": 7, "tokens_out": 3},
    )
    llm = ScriptedLLM(tmp_path)
    assert isinstance(llm, LLMClient)
    response = await llm.complete(Role.CODER, [], key="coder:s1.o1", schema=Answer)
    assert response.parsed == {"value": 2, "label": "x"}
    assert (response.usage.model, response.usage.tokens_in, response.usage.cost_usd) == (
        "fx",
        7,
        0.0,
    )
    assert llm.totals.calls == 1 and llm.totals.tokens_out == 3


async def test_parses_text_when_parsed_missing(tmp_path: Path) -> None:
    write(
        tmp_path,
        "planner.json",
        {
            "model": "fx",
            "text": '```json\n{"value": 9}\n```',
            "parsed": None,
            "tokens_in": 1,
            "tokens_out": 1,
        },
    )
    response = await ScriptedLLM(tmp_path, latency_s=0.001).complete(
        Role.PLANNER, [], key="planner", schema=Answer
    )
    assert response.parsed is not None and response.parsed["value"] == 9


async def test_missing_key(tmp_path: Path) -> None:
    with pytest.raises(LLMError, match="no scripted response for key 'judge:a.b'"):
        await ScriptedLLM(tmp_path).complete(Role.JUDGE, [], key="judge:a.b")


async def test_invalid_parsed(tmp_path: Path) -> None:
    write(tmp_path, "narrator.json", {"model": "fx", "text": "", "parsed": {"value": "no"}})
    with pytest.raises(LLMError, match="invalid"):
        await ScriptedLLM(tmp_path).complete(Role.NARRATOR, [], key="narrator", schema=Answer)


def test_fixture_name_never_leaves_the_directory() -> None:
    from borges.llm.scripted_provider import fixture_name

    name = fixture_name("coder:../../../x.o1")
    assert "/" not in name and ".." not in name and name.endswith(".json")
    assert fixture_name("coder:s1.o2:repair") == "coder__s1.o2__repair.json"
    assert "/" not in fixture_name("a\\b/c")


async def test_traversal_key_is_confined(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"text": "secret"}))
    inner = tmp_path / "fixtures"
    inner.mkdir()
    with pytest.raises(LLMError, match="no scripted response"):
        await ScriptedLLM(inner).complete(Role.CODER, [], key="../outside")
