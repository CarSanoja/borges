from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.llm.cache import DiskCache
from borges.llm.client import BudgetExceeded, LLMClient, LLMError, Role
from borges.llm.nebius_provider import NebiusLLM
from borges.llm.scripted_provider import ScriptedLLM
from borges.llm.spend import RunBudget, SpendLedger
from tests.llm.fakes import Answer, FakeClient, bad_request, completion

MESSAGES = [{"role": "system", "content": "be brief"}, {"role": "user", "content": "go"}]


def make(client: FakeClient, **kwargs) -> NebiusLLM:
    return NebiusLLM(api_key="k", base_url="https://example.test/v1/", client=client, **kwargs)


async def test_structured_call_sets_response_format_and_cost() -> None:
    client = FakeClient(completion('{"value": 1}', 1000, 200))
    llm = make(client)
    assert isinstance(llm, LLMClient)
    response = await llm.complete(Role.CODER, MESSAGES, key="coder:a.b", schema=Answer)
    call = client.calls[0]
    assert call["response_format"]["type"] == "json_schema"
    assert call["response_format"]["json_schema"]["schema"]["title"] == "Answer"
    assert "JSON schema" in call["messages"][0]["content"]
    assert call["messages"][0]["content"].startswith("be brief")
    assert call["max_tokens"] == 2048
    assert response.parsed == {"value": 1, "label": "x"}
    assert response.usage.cost_usd == pytest.approx((1000 * 0.06 + 200 * 0.24) / 1e6)
    assert llm.totals.calls == 1


async def test_plain_call_without_schema() -> None:
    client = FakeClient(completion("hello"))
    response = await make(client).complete(Role.NARRATOR, MESSAGES, key="narrator")
    assert "response_format" not in client.calls[0]
    assert response.text == "hello" and response.parsed is None


async def test_cache_hit_skips_call(tmp_path: Path) -> None:
    client = FakeClient(completion('{"value": 1}'))
    llm = make(client, cache=DiskCache(tmp_path))
    first = await llm.complete(Role.CODER, MESSAGES, key="k", schema=Answer)
    second = await llm.complete(Role.CODER, MESSAGES, key="k", schema=Answer)
    assert len(client.calls) == 1
    assert second.usage.cached and second.usage.cost_usd == 0
    assert second.parsed == first.parsed
    assert llm.totals.cached_calls == 1


async def test_budget_refusal_happens_before_calling(tmp_path: Path) -> None:
    client = FakeClient(completion("x"))
    ledger = SpendLedger(tmp_path / "spend.json", cap_usd=0.0000001)
    with pytest.raises(BudgetExceeded):
        await make(client, ledger=ledger).complete(
            Role.NARRATOR, MESSAGES, key="k", max_tokens=4096
        )
    assert client.calls == []
    with pytest.raises(BudgetExceeded):
        await make(client, run_budget=RunBudget(0.0000001)).complete(
            Role.NARRATOR, MESSAGES, key="k", max_tokens=4096
        )
    assert client.calls == []


async def test_spend_recorded_in_ledger_and_run_budget(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "spend.json", cap_usd=5)
    budget = RunBudget(1)
    llm = make(FakeClient(completion("x", 1000, 1000)), ledger=ledger, run_budget=budget)
    response = await llm.complete(Role.CODER, MESSAGES, key="k")
    assert ledger.total == pytest.approx(response.usage.cost_usd) == pytest.approx(budget.total)


async def test_schema_retry_appends_error() -> None:
    client = FakeClient(completion("not json", 10, 5), completion('{"value": 2}', 30, 7))
    llm = make(client)
    response = await llm.complete(Role.JUDGE, MESSAGES, key="k", schema=Answer)
    assert response.parsed is not None and response.parsed["value"] == 2
    retry_messages = client.calls[1]["messages"]
    assert retry_messages[-2] == {"role": "assistant", "content": "not json"}
    assert "invalid" in retry_messages[-1]["content"]
    assert (response.usage.tokens_in, response.usage.tokens_out) == (40, 12)


async def test_schema_failure_twice_raises() -> None:
    client = FakeClient(completion("nope"), completion('{"value": "x"}'))
    with pytest.raises(LLMError, match="after retry"):
        await make(client).complete(Role.JUDGE, MESSAGES, key="k", schema=Answer)
    assert len(client.calls) == 2


async def test_invalid_model_id_surfaces_instead_of_falling_back() -> None:
    client = FakeClient(bad_request("The model `nvidia/nope` does not exist"))
    with pytest.raises(LLMError, match="does not exist"):
        await make(client).complete(Role.PLANNER, MESSAGES, key="k", schema=Answer)
    assert len(client.calls) == 1


async def test_json_object_fallback_on_400() -> None:
    client = FakeClient(bad_request(), completion('{"value": 3}'))
    response = await make(client).complete(Role.PLANNER, MESSAGES, key="k", schema=Answer)
    assert client.calls[0]["response_format"]["type"] == "json_schema"
    assert client.calls[1]["response_format"] == {"type": "json_object"}
    assert response.parsed is not None and response.parsed["value"] == 3


async def test_think_tags_and_fences_in_live_text() -> None:
    client = FakeClient(completion('<think>hmm</think>```json\n{"value": 5}\n```'))
    response = await make(client).complete(Role.PLANNER, MESSAGES, key="k", schema=Answer)
    assert response.parsed is not None and response.parsed["value"] == 5


async def test_record_then_replay_round_trip(tmp_path: Path) -> None:
    record_dir = tmp_path / "fixtures"
    client = FakeClient(completion('{"value": 8, "label": "r"}', 50, 9))
    live = make(client, record_dir=record_dir)
    recorded = await live.complete(Role.CODER, MESSAGES, key="coder:s1.o2:repair", schema=Answer)
    path = record_dir / "coder__s1.o2__repair.json"
    assert set(json.loads(path.read_text())) == {
        "model",
        "text",
        "parsed",
        "tokens_in",
        "tokens_out",
    }
    replayed = await ScriptedLLM(record_dir).complete(
        Role.CODER, MESSAGES, key="coder:s1.o2:repair", schema=Answer
    )
    assert replayed.parsed == recorded.parsed
    assert replayed.usage.model == recorded.usage.model
    assert (replayed.usage.tokens_in, replayed.usage.tokens_out) == (50, 9)
    assert replayed.usage.cost_usd == 0.0


async def test_missing_usage_is_billed_at_the_estimate(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "spend.json", cap_usd=5)
    response = completion("x")
    response.usage = None
    llm = make(FakeClient(response), ledger=ledger)
    result = await llm.complete(Role.CODER, MESSAGES, key="k", max_tokens=1000)
    assert result.usage.cost_usd > 0
    assert ledger.total == pytest.approx(result.usage.cost_usd)
    assert llm.totals.cost_usd == pytest.approx(result.usage.cost_usd)


async def test_failed_schema_calls_are_still_in_totals(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "spend.json", cap_usd=5)
    client = FakeClient(completion("nope", 100, 10), completion("still no", 100, 10))
    llm = make(client, ledger=ledger)
    with pytest.raises(LLMError):
        await llm.complete(Role.JUDGE, MESSAGES, key="k", schema=Answer)
    assert llm.totals.calls == 2
    assert llm.totals.cost_usd == pytest.approx(ledger.total)


async def test_request_failure_releases_the_reservation(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "spend.json", cap_usd=0.01)
    budget = RunBudget(0.01)
    llm = make(FakeClient(bad_request(), completion("x", 10, 10)), ledger=ledger, run_budget=budget)
    with pytest.raises(LLMError):
        await llm.complete(Role.CODER, MESSAGES, key="k", max_tokens=100)
    await llm.complete(Role.CODER, MESSAGES, key="k2", max_tokens=100)


async def test_thinking_disabled_by_default_in_extra_body() -> None:
    client = FakeClient(completion("hello"))
    await make(client).complete(Role.NARRATOR, MESSAGES, key="narrator")
    assert client.calls[0]["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}


async def test_finish_reason_length_raises_without_retry() -> None:
    client = FakeClient(completion('{"value": 1', 10, 2048, finish_reason="length"))
    with pytest.raises(LLMError, match="coder:a.b: output truncated at max_tokens"):
        await make(client).complete(Role.CODER, MESSAGES, key="coder:a.b", schema=Answer)
    assert len(client.calls) == 1


async def test_truncated_call_is_still_billed(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "spend.json", cap_usd=5)
    client = FakeClient(completion("x", 1000, 1000, finish_reason="length"))
    with pytest.raises(LLMError):
        await make(client, ledger=ledger).complete(Role.CODER, MESSAGES, key="k")
    assert ledger.total > 0
