from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from borges.gateway.errors import GatewayDenied
from borges.llm.client import LLMResponse


@dataclass(frozen=True)
class ArmorContext:
    run_id: str
    agent_id: str
    principal: str
    model: str
    key: str


class ArmorBlocked(GatewayDenied):
    def __init__(self, reason: str, agent_id: str | None = None) -> None:
        super().__init__("armor", reason, agent_id)


class Armor(Protocol):
    def screen_input(
        self, context: ArmorContext, messages: list[dict[str, str]]
    ) -> list[dict[str, str]]: ...

    def screen_output(self, context: ArmorContext, response: LLMResponse) -> LLMResponse: ...


class NoopArmor:
    def screen_input(
        self, context: ArmorContext, messages: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        return messages

    def screen_output(self, context: ArmorContext, response: LLMResponse) -> LLMResponse:
        return response
