from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel

from borges.gateway.breaker import BreakerState, CircuitBreaker
from borges.gateway.guard import gateway_call
from borges.gateway.retry import backoff_delay, is_model_missing, is_transient
from borges.llm.client import LLMClient, LLMResponse, ModelSpec, Role
from borges.llm.model_override import use_model

if TYPE_CHECKING:
    from borges.gateway.core import Gateway

Observe = Callable[[str, str, str, str], None]


@dataclass(frozen=True)
class ModelCall:
    inner: LLMClient
    role: Role
    messages: list[dict[str, str]]
    key: str
    schema: type[BaseModel] | None
    max_tokens: int
    temperature: float


@dataclass
class ModelOutcome:
    response: LLMResponse | None
    attempts: int
    error: BaseException | None


async def run_model(
    gw: Gateway,
    call: ModelCall,
    model: str,
    estimate: float,
    override: ModelSpec | None,
    breaker: CircuitBreaker,
    observe: Observe,
) -> ModelOutcome:
    """Run one model's retry loop; every provider request reserves a call and its spend first."""
    agent_id = call.role.value
    last_error: BaseException | None = None
    attempts = 0
    for attempt in range(1, gw.policy.retry.max_attempts + 1):
        reservation = gw.budgets.reserve(agent_id, estimate)
        attempts += 1
        try:
            async with gw.budgets.slot(agent_id):
                with gateway_call(), use_model(override):
                    response = await call.inner.complete(
                        call.role,
                        call.messages,
                        key=call.key,
                        schema=call.schema,
                        max_tokens=call.max_tokens,
                        temperature=call.temperature,
                    )
        except Exception as exc:
            gw.budgets.release(reservation)
            if is_model_missing(exc):
                breaker.trip()
                observe("gateway.model_missing", agent_id, model, f"not served: {exc!r}"[:200])
                return ModelOutcome(None, attempts, exc)
            if not is_transient(exc):
                breaker.abandon_probe()
                raise
            breaker.record_failure()
            last_error = exc
            final = attempt == gw.policy.retry.max_attempts
            if final or breaker.state is BreakerState.OPEN:
                observe("gateway.retry", agent_id, model, f"giving up: {exc!r}"[:200])
                break
            delay = backoff_delay(gw.policy.retry, attempt, gw.rng)
            observe(
                "gateway.retry", agent_id, model, f"{type(exc).__name__}; retry in {delay:.2f}s"
            )
            await gw.sleep(delay)
            continue
        except BaseException:
            gw.budgets.release(reservation)
            breaker.abandon_probe()
            raise
        breaker.record_success()
        gw.budgets.settle(reservation, response.usage.cost_usd)
        return ModelOutcome(response, attempts, None)
    return ModelOutcome(None, attempts, last_error)
