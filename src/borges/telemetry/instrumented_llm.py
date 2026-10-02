from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from borges.fleet.principal import agent_principal
from borges.gateway.errors import GatewayDenied
from borges.llm.client import BudgetExceeded, LLMClient, LLMResponse, Role, UsageTotals
from borges.telemetry import hooks
from borges.telemetry.caller import calling_as, current_caller
from borges.telemetry.hashing import sha256_json, sha256_text
from borges.telemetry.llm_routing import gateway_data, route_call

GENAI_SYSTEM = "nebius"
SCRIPTED_MODEL = "scripted"


if TYPE_CHECKING:
    from borges.gateway.core import Gateway
    from borges.identity.run_identity import RunIdentity


class InstrumentedLLM:
    """Wraps an LLMClient so every model call yields a GenAI span and an audit record."""

    def __init__(
        self,
        inner: LLMClient,
        identity: RunIdentity | None = None,
        gateway: Gateway | None = None,
    ) -> None:
        self._inner = inner
        self._identity = identity
        self._gateway = gateway

    @property
    def totals(self) -> UsageTotals:
        return self._inner.totals

    def __getattr__(self, name: str) -> Any:
        value = getattr(self._inner, name)
        if callable(value):
            raise AttributeError(f"{name} is not reachable except through the gateway")
        return value

    def _request_model(self, role: Role) -> str:
        models = getattr(self._inner, "role_models", None)
        spec = models.get(role) if isinstance(models, dict) else None
        return spec.id if spec is not None else SCRIPTED_MODEL

    async def complete(
        self,
        role: Role,
        messages: list[dict[str, str]],
        *,
        key: str,
        schema: type[BaseModel] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> LLMResponse:
        agent_id = role.value
        token = self._identity.token_for(agent_id) if self._identity else None
        principal = current_caller().principal or agent_principal(agent_id)
        with calling_as(principal=principal, agent=agent_id, token=token):
            return await self._complete(
                role,
                messages,
                key=key,
                schema=schema,
                max_tokens=max_tokens,
                temperature=temperature,
            )

    async def _complete(
        self,
        role: Role,
        messages: list[dict[str, str]],
        *,
        key: str,
        schema: type[BaseModel] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> LLMResponse:
        if hooks.current() is None:
            response, _ = await route_call(
                self._inner, self._gateway, role, messages, key, schema, max_tokens, temperature
            )
            return response
        model = self._request_model(role)
        prompt_hash = sha256_json(
            {"messages": messages, "schema": schema.__name__ if schema else None}
        )
        caller = current_caller()
        attributes = {
            "gen_ai.system": GENAI_SYSTEM,
            "gen_ai.operation.name": "chat",
            "gen_ai.request.model": model,
            "gen_ai.request.max_tokens": max_tokens,
            "gen_ai.request.temperature": temperature,
            "borges.agent.role": role.value,
            "borges.llm.key": key,
            "borges.llm.provider": "scripted" if model == SCRIPTED_MODEL else "nebius",
            "borges.prompt.sha256": prompt_hash,
        }
        if caller.principal:
            attributes["borges.principal"] = caller.principal
        started = time.perf_counter()
        with hooks.span("model_call", f"chat {model}", **attributes) as span:
            try:
                response, routed = await route_call(
                    self._inner, self._gateway, role, messages, key, schema, max_tokens, temperature
                )
            except BaseException as exc:
                latency = time.perf_counter() - started
                span.set_attribute("error.type", type(exc).__name__)
                span.set_attribute("borges.latency_s", latency)
                denied = isinstance(exc, GatewayDenied | BudgetExceeded)
                reason = exc.reason if isinstance(exc, GatewayDenied) else "budget exceeded"
                hooks.audit(
                    "model.call",
                    decision="deny" if denied else None,
                    reason=reason if denied else None,
                    principal=caller.principal or agent_principal(role.value),
                    role=role.value,
                    model=model,
                    key=key,
                    step_id=caller.step_id,
                    option_id=caller.option_id,
                    prompt_sha256=prompt_hash,
                    latency_s=round(latency, 4),
                    outcome="refused" if denied else "error",
                    error_type=type(exc).__name__,
                )
                raise
            decision_data = gateway_data(self._gateway, routed, span)
            usage, latency = response.usage, time.perf_counter() - started
            response_hash = sha256_text(response.text)
            span.set_attribute("gen_ai.response.model", usage.model)
            span.set_attribute("gen_ai.usage.input_tokens", usage.tokens_in)
            span.set_attribute("gen_ai.usage.output_tokens", usage.tokens_out)
            span.set_attribute("borges.cache.hit", usage.cached)
            span.set_attribute("borges.cost_usd", usage.cost_usd)
            span.set_attribute("borges.latency_s", latency)
            span.set_attribute("borges.response.sha256", response_hash)
            hooks.audit(
                "model.call",
                decision="allow" if decision_data else None,
                principal=caller.principal or agent_principal(role.value),
                role=role.value,
                model=usage.model,
                key=key,
                step_id=caller.step_id,
                option_id=caller.option_id,
                prompt_sha256=prompt_hash,
                response_sha256=response_hash,
                tokens_in=usage.tokens_in,
                tokens_out=usage.tokens_out,
                cost_usd=usage.cost_usd,
                cache_hit=usage.cached,
                latency_s=round(latency, 4),
                outcome="ok",
                **decision_data,
            )
            return response


def instrument_llm(
    llm: LLMClient, identity: RunIdentity | None = None, gateway: Gateway | None = None
) -> LLMClient:
    return llm if isinstance(llm, InstrumentedLLM) else InstrumentedLLM(llm, identity, gateway)
