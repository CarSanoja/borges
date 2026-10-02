from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel

from borges.gateway.armor_hooks import ArmorContext
from borges.gateway.egress import enforce_egress
from borges.gateway.errors import GatewayDenied, GatewayUnavailable
from borges.gateway.llm_attempts import ModelCall, run_model
from borges.gateway.llm_models import (
    ModelChain,
    build_chain,
    estimate_cost,
    requested_model,
    resolve_spec,
)
from borges.gateway.policy_models import AgentPolicy
from borges.identity.actions import ToolAction
from borges.llm.client import LLMClient, LLMResponse, Role
from borges.llm.nebius_transport import estimate_prompt_tokens

if TYPE_CHECKING:
    from borges.gateway.core import Gateway


@dataclass
class Routed:
    response: LLMResponse
    model: str
    attempts: int
    fallback: bool
    rows_stripped: int
    estimate_usd: float


class LLMRoute:
    def __init__(self, gateway: Gateway) -> None:
        self.gw = gateway

    async def complete(
        self,
        inner: LLMClient,
        role: Role,
        messages: list[dict[str, str]],
        *,
        key: str,
        schema: type[BaseModel] | None,
        max_tokens: int,
        temperature: float,
    ) -> Routed:
        agent_id = role.value
        try:
            return await self._complete(
                inner, agent_id, role, messages, key, schema, max_tokens, temperature
            )
        except GatewayDenied as denied:
            if not denied.audited:
                self.gw.record_denial(denied, key=key)
            raise

    def _prepare(
        self,
        inner: LLMClient,
        agent_id: str,
        role: Role,
        messages: list[dict[str, str]],
        max_tokens: int,
        key: str,
    ) -> tuple[AgentPolicy, ModelChain, list[dict[str, str]], int]:
        gw = self.gw
        agent = gw.loaded.agent(agent_id)
        if agent is None:
            raise gw.deny("policy", f"no gateway policy for agent {agent_id!r}", agent_id, key=key)
        requested = requested_model(inner, role)
        chain = build_chain(agent, requested, gw.local_model)
        if chain is None:
            raise gw.deny(
                "model",
                f"model {requested!r} is not allowed for {agent_id}; allowed: {agent.models}",
                agent_id,
                key=key,
            )
        gw.authorize(agent_id, ToolAction(tool="model.invoke", target=chain.auth_target))
        if max_tokens > agent.max_tokens:
            raise gw.deny(
                "max_tokens",
                f"max_tokens {max_tokens} is above the ceiling {agent.max_tokens} for {agent_id}",
                agent_id,
                key=key,
            )
        report = enforce_egress(messages, agent, gw.dataset_columns)
        if report.violations:
            raise gw.deny("egress", "; ".join(report.violations), agent_id, key=key)
        if report.changed:
            gw.audit(
                "gateway.egress",
                decision="observe",
                reason=f"stripped {report.rows_stripped} and redacted {report.rows_redacted} "
                f"sample rows above the {agent.egress!r} class",
                principal=gw.principal_of(agent_id),
                agent=agent_id,
                key=key,
            )
        return agent, chain, report.messages, report.rows_stripped

    async def _complete(
        self,
        inner: LLMClient,
        agent_id: str,
        role: Role,
        messages: list[dict[str, str]],
        key: str,
        schema: type[BaseModel] | None,
        max_tokens: int,
        temperature: float,
    ) -> Routed:
        gw = self.gw
        _, chain, sent, stripped = self._prepare(inner, agent_id, role, messages, max_tokens, key)
        context = ArmorContext(gw.run_id, agent_id, gw.principal_of(agent_id), chain.models[0], key)
        sent = gw.armor.screen_input(context, sent)
        tokens_in = estimate_prompt_tokens(sent)
        last_error: BaseException | None = None
        attempts = 0
        for index, model in enumerate(chain.models):
            breaker = gw.breakers.of(model)
            if not breaker.allow():
                self._observe("gateway.breaker", agent_id, model, "circuit open; model skipped")
                continue
            spec = resolve_spec(inner, model)
            if index > 0:
                self._observe("gateway.fallback", agent_id, model, "falling back to the next model")
                gw.authorize(agent_id, ToolAction(tool="model.invoke", target=model))
                if spec is None:
                    raise gw.deny("model", f"no pricing known for model {model!r}", agent_id)
            estimate = estimate_cost(spec, tokens_in, max_tokens)
            call = ModelCall(inner, role, sent, key, schema, max_tokens, temperature)
            outcome = await run_model(
                gw, call, model, estimate, spec if index > 0 else None, breaker, self._observe
            )
            attempts += outcome.attempts
            if outcome.response is not None:
                response = gw.armor.screen_output(context, outcome.response)
                return Routed(response, model, attempts, index > 0, stripped, estimate)
            last_error = outcome.error
        if last_error is not None:
            raise last_error
        raise GatewayUnavailable(
            "breaker", f"circuit open for every allowed model of {agent_id}", agent_id
        )

    def _observe(self, kind: str, agent_id: str, model: str, reason: str) -> None:
        self.gw.audit(
            kind,
            decision="observe",
            reason=reason,
            principal=self.gw.principal_of(agent_id),
            agent=agent_id,
            model=model,
        )
