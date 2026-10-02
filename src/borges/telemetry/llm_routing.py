from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from borges.llm.client import LLMClient, LLMResponse, Role

if TYPE_CHECKING:
    from borges.gateway.core import Gateway
    from borges.gateway.llm_route import Routed


async def route_call(
    inner: LLMClient,
    gateway: Gateway | None,
    role: Role,
    messages: list[dict[str, str]],
    key: str,
    schema: type[BaseModel] | None,
    max_tokens: int,
    temperature: float,
) -> tuple[LLMResponse, Routed | None]:
    if gateway is None:
        response = await inner.complete(
            role,
            messages,
            key=key,
            schema=schema,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response, None
    routed = await gateway.llm.complete(
        inner,
        role,
        messages,
        key=key,
        schema=schema,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return routed.response, routed


def gateway_data(gateway: Gateway | None, routed: Routed | None, span: Any) -> dict[str, Any]:
    if gateway is None or routed is None:
        return {}
    data = {
        "policy_sha": gateway.policy_sha,
        "attempts": routed.attempts,
        "fallback": routed.fallback,
        "egress_rows_stripped": routed.rows_stripped,
    }
    for name, value in data.items():
        span.set_attribute(f"borges.gateway.{name}", value)
    return data
