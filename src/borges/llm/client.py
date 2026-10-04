from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class Role(StrEnum):
    PLANNER = "planner"
    CODER = "coder"
    REPAIRER = "repairer"
    ADVERSARY = "adversary"
    JUDGE = "judge"
    REVIEWER = "reviewer"
    NARRATOR = "narrator"


class ModelSpec(BaseModel):
    id: str
    input_usd_per_m: float
    output_usd_per_m: float
    thinking: bool = False

    def cost(self, tokens_in: int, tokens_out: int) -> float:
        return (tokens_in * self.input_usd_per_m + tokens_out * self.output_usd_per_m) / 1e6


NANO = ModelSpec(
    id="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", input_usd_per_m=0.06, output_usd_per_m=0.24
)
LIGHTNING = ModelSpec(
    id="nvidia/Nemotron-3_5-Lightning", input_usd_per_m=0.06, output_usd_per_m=0.24
)
SUPER = ModelSpec(id="nvidia/nemotron-3-super-120b-a12b", input_usd_per_m=0.3, output_usd_per_m=0.9)
ULTRA = ModelSpec(id="nvidia/Nemotron-3-Ultra-550b-a55b", input_usd_per_m=1.0, output_usd_per_m=3.0)

KNOWN_MODELS: dict[str, ModelSpec] = {m.id: m for m in (NANO, LIGHTNING, SUPER, ULTRA)}

DEFAULT_ROLE_MODELS: dict[Role, ModelSpec] = {
    Role.PLANNER: SUPER,
    Role.CODER: LIGHTNING,
    Role.REPAIRER: SUPER,
    Role.ADVERSARY: SUPER,
    Role.JUDGE: SUPER,
    Role.REVIEWER: SUPER,
    Role.NARRATOR: ULTRA,
}


class Usage(BaseModel):
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    cached: bool = False


class LLMResponse(BaseModel):
    role: Role
    text: str
    parsed: dict[str, Any] | None = None
    usage: Usage
    latency_s: float = 0.0


class UsageTotals(BaseModel):
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    calls: int = 0
    cached_calls: int = 0
    by_model: dict[str, float] = Field(default_factory=dict)

    def add(self, usage: Usage) -> None:
        self.calls += 1
        self.cached_calls += int(usage.cached)
        self.tokens_in += usage.tokens_in
        self.tokens_out += usage.tokens_out
        self.cost_usd += usage.cost_usd
        self.by_model[usage.model] = self.by_model.get(usage.model, 0.0) + usage.cost_usd


class BudgetExceeded(RuntimeError):
    pass


class LLMError(RuntimeError):
    pass


@runtime_checkable
class LLMClient(Protocol):
    """Role-routed chat completion.

    `schema` is a pydantic model class: the provider requests JSON that follows its JSON
    schema, validates it, retries once on invalid output, and returns it in `parsed`.
    `key` is a stable identifier of the request purpose (e.g. "coder:d2.o1"), used by the
    scripted provider to look up recorded responses and by caches/logs.
    """

    totals: UsageTotals

    async def complete(
        self,
        role: Role,
        messages: list[dict[str, str]],
        *,
        key: str,
        schema: type[BaseModel] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> LLMResponse: ...
