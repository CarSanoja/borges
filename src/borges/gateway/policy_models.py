from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EgressClass = Literal["none", "profile_only", "sample_rows"]
EGRESS_RANK: dict[str, int] = {"none": 0, "profile_only": 1, "sample_rows": 2}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RetryPolicy(Strict):
    max_attempts: int = Field(ge=1, le=10)
    base_delay_s: float = Field(ge=0)
    max_delay_s: float = Field(ge=0)
    jitter: float = Field(ge=0, le=1)


class BreakerPolicy(Strict):
    failure_threshold: int = Field(ge=1)
    cooldown_s: float = Field(gt=0)


class RunLimits(Strict):
    max_calls: int = Field(ge=1)
    max_cost_usd: float = Field(gt=0)
    max_concurrent_calls: int = Field(ge=1)
    max_sandbox_execs: int = Field(ge=1)
    max_concurrent_sandbox_execs: int = Field(ge=1)


class AgentPolicy(Strict):
    models: list[str] = Field(min_length=1)
    max_tokens: int = Field(ge=1)
    max_calls_per_run: int = Field(ge=1)
    max_cost_usd_per_run: float = Field(gt=0)
    max_concurrent_calls: int = Field(ge=1)
    egress: EgressClass
    max_sample_rows: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _consistent(self) -> AgentPolicy:
        if len(set(self.models)) != len(self.models):
            raise ValueError("models lists a model twice")
        if self.egress != "sample_rows" and self.max_sample_rows:
            raise ValueError("max_sample_rows needs egress 'sample_rows'")
        if self.egress == "sample_rows" and self.max_sample_rows < 1:
            raise ValueError("egress 'sample_rows' needs max_sample_rows >= 1")
        return self

    @property
    def primary(self) -> str:
        return self.models[0]

    @property
    def fallbacks(self) -> list[str]:
        return self.models[1:]


class SandboxPolicy(Strict):
    executor: str
    require_code_guard: bool
    allowed_commands: list[str] = Field(min_length=1)
    step_dir: str
    data_file: str
    max_timeout_s: float = Field(gt=0)
    network: Literal["none"]


class GatewayPolicy(Strict):
    version: int
    description: str = ""
    retry: RetryPolicy
    breaker: BreakerPolicy
    run: RunLimits
    sandbox: SandboxPolicy
    agents: dict[str, AgentPolicy]

    @model_validator(mode="after")
    def _retry_bounds(self) -> GatewayPolicy:
        if self.retry.max_delay_s < self.retry.base_delay_s:
            raise ValueError("retry.max_delay_s is below retry.base_delay_s")
        return self
