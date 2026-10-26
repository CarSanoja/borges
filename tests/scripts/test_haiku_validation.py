from __future__ import annotations

import importlib
import json
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel

from borges.llm.client import BudgetExceeded, LLMError, Role


class Ping(BaseModel):
    ok: bool


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("haiku_validation_client").HaikuValidationLLM


def completion(stop_reason="end_turn"):
    return {
        "model": "claude-haiku-5-5",
        "content": [{"type": "text", "text": '{"ok": true}'}],
        "usage": {"input_tokens": 20, "output_tokens": 5},
        "stop_reason": stop_reason,
    }


async def test_native_request_validates_json_and_charges_reported_tokens(provider, tmp_path):
    sent = []

    def respond(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json=completion())

    async with httpx.AsyncClient(
        base_url="https://api.anthropic.com/v1/", transport=httpx.MockTransport(respond)
    ) as client:
        llm = provider("test-only", tmp_path, 0.25, 0.50, client=client)
        result = await llm.complete(
            Role.PLANNER, [{"role": "user", "content": "Reply OK"}], key="ping", schema=Ping
        )
    assert result.parsed == {"ok": True}
    assert sent[0]["model"] == "claude-haiku-5-5"
    assert "temperature" not in sent[0]
    assert sent[0]["thinking"] == {"type": "disabled"}
    assert "JSON schema" in sent[0]["system"]
    assert llm.totals.tokens_in == 20 and llm.totals.tokens_out == 5
    assert llm.ledger.total == pytest.approx(0.0000045)


async def test_budget_refuses_before_any_network_call(provider, tmp_path):
    def unexpected(request):
        pytest.fail("budget-exceeding call reached the network")

    async with httpx.AsyncClient(
        base_url="https://api.anthropic.com/v1/", transport=httpx.MockTransport(unexpected)
    ) as client:
        llm = provider("test-only", tmp_path, 0.00000001, 0.50, client=client)
        with pytest.raises(BudgetExceeded):
            await llm.complete(Role.PLANNER, [{"role": "user", "content": "Reply OK"}], key="cap")
    assert llm.totals.calls == 0


async def test_truncated_response_is_charged_and_not_accepted(provider, tmp_path):
    async with httpx.AsyncClient(
        base_url="https://api.anthropic.com/v1/",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=completion("max_tokens"))
        ),
    ) as client:
        llm = provider("test-only", tmp_path, 0.25, 0.50, client=client)
        with pytest.raises(LLMError, match="output truncated"):
            await llm.complete(Role.PLANNER, [{"role": "user", "content": "Reply OK"}], key="short")
    assert llm.totals.calls == 1 and llm.ledger.total > 0
