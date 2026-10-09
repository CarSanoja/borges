from __future__ import annotations

import asyncio
import dataclasses
import json
from typing import Any

import pytest

from borges.gateway.armor_hooks import ArmorBlocked
from borges.gateway.errors import GatewayBudgetExceeded, GatewayDenied, GatewayUnavailable
from borges.gateway.policy_load import LoadedPolicy, policy_for
from borges.identity.agent_tokens import process_issuer
from borges.llm.client import LIGHTNING, SUPER, ULTRA, LLMResponse, Role
from borges.telemetry.caller import calling_as

from .conftest import RUN, FakeLLM

MSG = [{"role": "user", "content": "hello"}]


class Status(Exception):
    def __init__(self, code: int) -> None:
        super().__init__(f"http {code}")
        self.status_code = code


def tweak(loaded: LoadedPolicy, agent: str | None = None, **changes: Any) -> LoadedPolicy:
    policy = loaded.policy.model_copy(deep=True)
    if agent:
        policy.agents[agent] = policy.agents[agent].model_copy(update=changes)
    return dataclasses.replace(loaded, policy=policy)


async def ask(gateway, llm, role=Role.PLANNER, messages=MSG, max_tokens=100, key="k"):
    return await gateway.llm.complete(
        llm, role, messages, key=key, schema=None, max_tokens=max_tokens, temperature=0.2
    )


async def test_allowed_call_goes_through_and_is_marked_inside_the_gateway(make_gateway) -> None:
    gateway, llm = make_gateway(), FakeLLM()
    routed = await ask(gateway, llm)
    assert routed.model == SUPER.id and routed.attempts == 1 and not routed.fallback
    assert llm.calls[0]["inside"] is True


async def test_missing_token_is_denied_and_audited(make_gateway, audit) -> None:
    llm = FakeLLM()
    with pytest.raises(GatewayDenied, match="no agent token"):
        await ask(make_gateway(identity=None), llm)
    assert not llm.calls
    assert audit.denials()[0]["rule"] == "identity" and audit.denials()[0]["kind"] == "gateway.deny"


async def test_forged_token_is_denied(make_gateway, audit) -> None:
    llm = FakeLLM()
    with calling_as(agent="planner", token="e30.deadbeef"), pytest.raises(GatewayDenied) as caught:
        await ask(make_gateway(), llm)
    assert caught.value.rule == "identity" and not llm.calls
    assert any(r["kind"] == "identity.authorize" and r["decision"] == "deny" for r in audit.records)


async def test_expired_token_is_denied(make_gateway) -> None:
    gateway = make_gateway()
    issuer = process_issuer()
    token = issuer.mint(RUN, "agent://borges/planner", {"llm.invoke:" + SUPER.id}, ttl_s=-5)
    with calling_as(agent="planner", token=token), pytest.raises(GatewayDenied, match="expired"):
        await ask(gateway, FakeLLM())


async def test_token_of_another_run_is_denied(make_gateway) -> None:
    gateway = make_gateway()
    token = process_issuer().mint(
        "r_other", "agent://borges/planner", {"llm.invoke:" + SUPER.id}, ttl_s=60
    )
    with calling_as(agent="planner", token=token), pytest.raises(GatewayDenied, match="wrong_run"):
        await ask(gateway, FakeLLM())


async def test_another_agents_token_is_denied(make_gateway) -> None:
    gateway = make_gateway()
    coder_token = gateway.identity.token_for("coder")
    with (
        calling_as(agent="planner", token=coder_token),
        pytest.raises(GatewayDenied, match="wrong_agent"),
    ):
        await ask(gateway, FakeLLM())


async def test_capability_the_agent_does_not_hold_is_denied(make_gateway, settings, audit) -> None:
    loaded = tweak(policy_for(settings), "coder", models=[LIGHTNING.id, SUPER.id])
    llm = FakeLLM([Status(503)] * 3)
    with pytest.raises(GatewayDenied) as caught:
        await ask(make_gateway(loaded=loaded), llm, Role.CODER)
    assert caught.value.rule == "capability" and len(llm.calls) == 3
    assert audit.of("identity.authorize")[-1]["decision"] == "deny"


async def test_model_outside_the_policy_chain_is_denied(make_gateway, audit) -> None:
    llm = FakeLLM(role_models={Role.CODER: ULTRA})
    with pytest.raises(GatewayDenied, match="not allowed for coder"):
        await ask(make_gateway(), llm, Role.CODER)
    assert not llm.calls and audit.denials()[0]["rule"] == "model"


async def test_agent_without_policy_is_denied(make_gateway, settings) -> None:
    loaded = policy_for(settings)
    policy = loaded.policy.model_copy(deep=True)
    del policy.agents["judge"]
    with pytest.raises(GatewayDenied, match="no gateway policy"):
        await ask(
            make_gateway(loaded=dataclasses.replace(loaded, policy=policy)), FakeLLM(), Role.JUDGE
        )


async def test_max_tokens_above_the_ceiling_is_denied(make_gateway, audit) -> None:
    llm = FakeLLM()
    with pytest.raises(GatewayDenied, match="ceiling"):
        await ask(make_gateway(), llm, Role.JUDGE, max_tokens=999999)
    assert not llm.calls and audit.denials()[0]["rule"] == "max_tokens"


async def test_sample_rows_are_stripped_for_a_profile_only_agent(make_gateway, audit) -> None:
    body = {"columns": [], "sample_rows": [{"a": 1}, {"a": 2}]}
    messages = [{"role": "user", "content": "P: " + json.dumps(body, separators=(",", ":"))}]
    llm = FakeLLM()
    routed = await ask(make_gateway(), llm, Role.JUDGE, messages)
    assert '"sample_rows":[]' in llm.calls[0]["messages"][0]["content"]
    assert routed.rows_stripped == 2
    assert audit.of("gateway.egress")[0]["decision"] == "observe"


async def test_raw_rows_to_a_profile_only_agent_are_denied(make_gateway, audit) -> None:
    gateway = make_gateway(dataset_columns=frozenset({"a", "b", "c"}))
    rows = [{"a": i, "b": i, "c": i} for i in range(9)]
    llm = FakeLLM()
    with pytest.raises(GatewayDenied, match="9 raw data rows") as caught:
        await ask(gateway, llm, Role.NARRATOR, [{"role": "user", "content": json.dumps(rows)}])
    assert caught.value.rule == "egress" and not llm.calls
    assert audit.denials()[0]["decision"] == "deny"


class RecordingArmor:
    def __init__(self, block: bool = False) -> None:
        self.block = block
        self.contexts: list[Any] = []

    def screen_input(self, context, messages):
        self.contexts.append(context)
        if self.block:
            raise ArmorBlocked("injection marker", context.agent_id)
        return [{**messages[0], "content": messages[0]["content"] + " [screened]"}]

    def screen_output(self, context, response: LLMResponse) -> LLMResponse:
        return response.model_copy(update={"text": "out-screened"})


async def test_armor_hooks_run_after_egress_and_around_the_call(make_gateway) -> None:
    armor = RecordingArmor()
    llm = FakeLLM()
    routed = await ask(make_gateway(armor=armor), llm)
    assert llm.calls[0]["messages"][0]["content"] == "hello [screened]"
    assert routed.response.text == "out-screened"
    assert armor.contexts[0].agent_id == "planner" and armor.contexts[0].run_id == RUN


async def test_armor_block_is_a_denied_and_audited_call(make_gateway, audit) -> None:
    llm = FakeLLM()
    with pytest.raises(ArmorBlocked):
        await ask(make_gateway(armor=RecordingArmor(block=True)), llm)
    assert not llm.calls and audit.denials()[0]["rule"] == "armor"


async def test_default_armor_leaves_messages_alone(make_gateway) -> None:
    llm = FakeLLM()
    await ask(make_gateway(), llm)
    assert llm.calls[0]["messages"] == MSG


async def test_call_budget_is_per_agent(make_gateway, settings, audit) -> None:
    gateway = make_gateway(loaded=tweak(policy_for(settings), "judge", max_calls_per_run=2))
    llm = FakeLLM()
    await ask(gateway, llm, Role.JUDGE)
    await ask(gateway, llm, Role.JUDGE)
    with pytest.raises(GatewayBudgetExceeded):
        await ask(gateway, llm, Role.JUDGE)
    assert len(llm.calls) == 2
    await ask(gateway, llm, Role.REVIEWER)
    assert audit.denials()[0]["rule"] == "budget" and audit.denials()[0]["agent"] == "judge"


async def test_cost_budget_is_reserved_before_the_call(make_gateway, settings) -> None:
    gateway = make_gateway(loaded=tweak(policy_for(settings), "judge", max_cost_usd_per_run=1e-9))
    llm = FakeLLM()
    with pytest.raises(GatewayBudgetExceeded, match="cost limit"):
        await ask(gateway, llm, Role.JUDGE, max_tokens=500)
    assert not llm.calls


async def test_actual_cost_is_settled_into_the_ledger(make_gateway) -> None:
    gateway = make_gateway()
    await ask(gateway, FakeLLM([0.05]), Role.JUDGE)
    snapshot = gateway.budgets.snapshot()
    assert snapshot["judge"]["spent_usd"] == 0.05 and snapshot["run"]["reserved_usd"] == 0.0


async def test_transient_errors_are_retried_with_exponential_backoff(make_gateway, naps) -> None:
    llm = FakeLLM([Status(503), Status(500), None])
    routed = await ask(make_gateway(), llm)
    assert routed.attempts == 3 and len(llm.calls) == 3
    assert naps.delays == [0.5, 1.0]


async def test_timeouts_are_retried(make_gateway, naps) -> None:
    routed = await ask(make_gateway(), FakeLLM([TimeoutError(), None]))
    assert routed.attempts == 2 and naps.delays == [0.5]


async def test_non_transient_errors_are_not_retried(make_gateway, naps) -> None:
    llm = FakeLLM([Status(400)])
    with pytest.raises(Status):
        await ask(make_gateway(), llm)
    assert len(llm.calls) == 1 and not naps.delays


async def test_exhausted_retries_raise_the_last_error_and_release_the_budget(make_gateway) -> None:
    gateway = make_gateway()
    llm = FakeLLM([Status(503)] * 3)
    with pytest.raises(Status):
        await ask(gateway, llm, Role.JUDGE)
    assert len(llm.calls) == 3 and gateway.budgets.snapshot()["judge"]["reserved_usd"] == 0.0


async def test_breaker_opens_refuses_and_closes_after_a_good_probe(make_gateway, clock) -> None:
    gateway = make_gateway()
    llm = FakeLLM([Status(503)] * 4)
    with pytest.raises(Status):
        await ask(gateway, llm, Role.JUDGE)
    with pytest.raises(Status):
        await ask(gateway, llm, Role.JUDGE)
    assert len(llm.calls) == 4 and gateway.breakers.states()[SUPER.id] == "open"
    with pytest.raises(GatewayUnavailable, match="circuit open"):
        await ask(gateway, llm, Role.JUDGE)
    assert len(llm.calls) == 4
    clock.now += 31
    await ask(gateway, llm, Role.JUDGE)
    assert gateway.breakers.states()[SUPER.id] == "closed"
    await ask(gateway, llm, Role.JUDGE)


async def test_failed_probe_keeps_the_breaker_open(make_gateway, clock) -> None:
    gateway = make_gateway()
    llm = FakeLLM([Status(503)] * 5)
    for _ in range(2):
        with pytest.raises(Status):
            await ask(gateway, llm, Role.JUDGE)
    clock.now += 31
    with pytest.raises(Status):
        await ask(gateway, llm, Role.JUDGE)
    assert gateway.breakers.states()[SUPER.id] == "open"
    with pytest.raises(GatewayUnavailable):
        await ask(gateway, llm, Role.JUDGE)


async def test_fallback_to_the_next_listed_model(make_gateway, audit) -> None:
    llm = FakeLLM([Status(503)] * 3)
    routed = await ask(make_gateway(), llm, Role.PLANNER)
    assert routed.fallback and routed.model == ULTRA.id
    assert [c["model"] for c in llm.calls] == [SUPER.id] * 3 + [ULTRA.id]
    assert audit.of("gateway.fallback")[0]["model"] == ULTRA.id


async def test_a_model_the_provider_no_longer_serves_falls_back_and_is_skipped(
    make_gateway, audit
) -> None:
    gateway = make_gateway()
    llm = FakeLLM([Status(404)])
    routed = await ask(gateway, llm, Role.PLANNER)
    assert routed.fallback and routed.model == ULTRA.id
    assert [c["model"] for c in llm.calls] == [SUPER.id, ULTRA.id]
    assert gateway.breakers.states()[SUPER.id] == "open"
    assert audit.of("gateway.model_missing")[0]["model"] == SUPER.id
    again = await ask(gateway, llm, Role.PLANNER)
    assert again.model == ULTRA.id and [c["model"] for c in llm.calls][-1] == ULTRA.id
    assert len(llm.calls) == 3


async def test_no_fallback_when_the_policy_lists_none(make_gateway) -> None:
    llm = FakeLLM([Status(503)] * 3)
    with pytest.raises(Status):
        await ask(make_gateway(), llm, Role.CODER)
    assert {c["model"] for c in llm.calls} == {LIGHTNING.id}


async def test_open_breaker_sends_the_call_straight_to_the_fallback(make_gateway) -> None:
    gateway = make_gateway()
    for _ in range(4):
        gateway.breakers.of(SUPER.id).record_failure()
    llm = FakeLLM()
    routed = await ask(gateway, llm, Role.PLANNER)
    assert routed.model == ULTRA.id and [c["model"] for c in llm.calls] == [ULTRA.id]


async def test_concurrency_is_capped_per_agent(make_gateway, settings) -> None:
    gateway = make_gateway(loaded=tweak(policy_for(settings), "judge", max_concurrent_calls=2))

    class Slow(FakeLLM):
        active = peak = 0

        async def complete(self, *args, **kwargs):
            Slow.active += 1
            Slow.peak = max(Slow.peak, Slow.active)
            await asyncio.sleep(0.01)
            Slow.active -= 1
            return await super().complete(*args, **kwargs)

    llm = Slow()
    await asyncio.gather(*(ask(gateway, llm, Role.JUDGE) for _ in range(6)))
    assert Slow.peak == 2


async def test_scripted_replay_is_allowed_and_authorised_as_the_primary(make_gateway) -> None:
    llm = FakeLLM()
    llm.role_models = None
    routed = await ask(make_gateway(), llm, Role.JUDGE)
    assert routed.model == "scripted"


async def test_local_model_is_allowed_only_when_the_run_is_local(make_gateway) -> None:
    from borges.llm.client import ModelSpec

    local = ModelSpec(id="nemotron-3-nano:30b", input_usd_per_m=0, output_usd_per_m=0)
    llm = FakeLLM(role_models={Role.JUDGE: local})
    with pytest.raises(GatewayDenied, match="not allowed"):
        await ask(make_gateway(), llm, Role.JUDGE)
    routed = await ask(make_gateway(local_model=local.id), llm, Role.JUDGE)
    assert routed.model == local.id
