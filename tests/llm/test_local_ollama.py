from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from borges.config import Settings
from borges.llm.client import LLMError, Role
from borges.llm.factory import make_llm
from borges.llm.local_models import local_role_models, ollama_thinking_body
from borges.llm.nebius_provider import NebiusLLM
from tests.llm.fakes import FakeClient


class Sum(BaseModel):
    answer: int
    label: str


FIXTURES = Path(__file__).parent / "fixtures"
MESSAGES = [{"role": "user", "content": "go"}]


def recorded(name: str) -> SimpleNamespace:
    raw = json.loads((FIXTURES / name).read_text())
    choice = raw["choices"][0]
    message = SimpleNamespace(**choice["message"])
    usage = raw["usage"]
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason=choice["finish_reason"])],
        usage=SimpleNamespace(
            prompt_tokens=usage["prompt_tokens"], completion_tokens=usage["completion_tokens"]
        ),
    )


def local(client: FakeClient, **kwargs: Any) -> NebiusLLM:
    return NebiusLLM(
        api_key="ollama",
        base_url="http://localhost:11434/v1",
        role_models=local_role_models("nemotron-3-nano:30b"),
        thinking_body=ollama_thinking_body,
        client=client,
        **kwargs,
    )


def test_thinking_switch_is_reasoning_effort_none() -> None:
    assert ollama_thinking_body(False) == {"reasoning_effort": "none"}
    assert ollama_thinking_body(True) == {}


@pytest.mark.parametrize(
    "name",
    [
        "ollama_think_default.json",
        "ollama_effort_none.json",
        "ollama_schema_think.json",
        "ollama_schema_none.json",
    ],
)
async def test_real_ollama_responses_parse_and_keep_reasoning_out(name: str) -> None:
    raw = json.loads((FIXTURES / name).read_text())
    assert "<think>" not in raw["choices"][0]["message"]["content"]
    client = FakeClient(recorded(name))
    response = await local(client).complete(Role.JUDGE, MESSAGES, key="k", schema=Sum)
    assert response.parsed is not None and response.parsed["answer"] == 42
    assert response.usage.tokens_out == raw["usage"]["completion_tokens"]
    assert response.usage.cost_usd == 0.0


async def test_reasoning_field_never_reaches_the_text() -> None:
    client = FakeClient(recorded("ollama_think_default.json"))
    response = await local(client).complete(Role.PLANNER, MESSAGES, key="k")
    assert "We need to output JSON" not in response.text
    assert json.loads(response.text) == {"answer": 42, "label": "sum"}


async def test_truncated_thinking_reply_is_a_clear_error() -> None:
    client = FakeClient(recorded("ollama_truncated_thinking.json"))
    with pytest.raises(LLMError, match="truncated"):
        await local(client).complete(Role.PLANNER, MESSAGES, key="planner:x", max_tokens=40)


async def test_requests_disable_thinking_only_for_coder_and_narrator() -> None:
    client = FakeClient(*[recorded("ollama_effort_none.json") for _ in Role])
    llm = local(client)
    for role in Role:
        await llm.complete(role, MESSAGES, key=role.value)
    sent = {role: call["extra_body"] for role, call in zip(Role, client.calls, strict=True)}
    assert sent[Role.CODER] == {"reasoning_effort": "none"}
    assert sent[Role.NARRATOR] == {"reasoning_effort": "none"}
    assert sent[Role.PLANNER] == sent[Role.ADVERSARY] == sent[Role.JUDGE] == {}
    assert sent[Role.REVIEWER] == {"reasoning_effort": "none"}


async def test_nebius_keeps_chat_template_switch() -> None:
    client = FakeClient(recorded("ollama_effort_none.json"))
    llm = NebiusLLM(api_key="k", base_url="https://example.test/v1/", client=client)
    await llm.complete(Role.CODER, MESSAGES, key="k")
    assert client.calls[0]["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}


def test_factory_local_uses_the_ollama_switch(tmp_path: Path) -> None:
    llm = make_llm(Settings(_env_file=None, borges_home=tmp_path), mode="local")
    assert llm.thinking_body is ollama_thinking_body


async def test_truncated_thinking_reply_is_retried_without_thinking() -> None:
    client = FakeClient(
        recorded("ollama_truncated_thinking.json"), recorded("ollama_effort_none.json")
    )
    llm = local(client, retry_truncated_without_thinking=True)
    response = await llm.complete(Role.PLANNER, MESSAGES, key="planner:x", max_tokens=40)
    assert client.calls[0]["extra_body"] == {}
    assert client.calls[1]["extra_body"] == {"reasoning_effort": "none"}
    assert json.loads(response.text) == {"answer": 42, "label": "sum"}


async def test_retry_without_thinking_still_fails_when_quiet_reply_is_truncated() -> None:
    truncated = recorded("ollama_truncated_thinking.json")
    client = FakeClient(truncated, truncated)
    llm = local(client, retry_truncated_without_thinking=True)
    with pytest.raises(LLMError, match="planner:x: output truncated"):
        await llm.complete(Role.PLANNER, MESSAGES, key="planner:x", max_tokens=40)
    assert len(client.calls) == 2


def test_local_factory_enables_the_thinking_retry() -> None:
    llm = make_llm(Settings(_env_file=None), "local")
    assert isinstance(llm, NebiusLLM) and llm.retry_truncated_without_thinking
