from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from borges.config import REPO_ROOT, Settings
from borges.gateway.core import Gateway, quiet_sandbox_allows
from borges.gateway.guard import inside_gateway
from borges.gateway.policy_load import policy_for
from borges.identity.fleet_authorizer import fleet_authorizer
from borges.identity.run_identity import mint_run_identity
from borges.llm.client import (
    LIGHTNING,
    SUPER,
    LLMResponse,
    ModelSpec,
    Role,
    Usage,
    UsageTotals,
)
from borges.llm.model_override import model_override

RUN = "r_test"


class Audit:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def __call__(self, kind: str, **fields: Any) -> None:
        self.records.append({"kind": kind, **fields})

    def of(self, kind: str) -> list[dict[str, Any]]:
        return [r for r in self.records if r["kind"] == kind]

    def denials(self) -> list[dict[str, Any]]:
        return [r for r in self.records if r.get("decision") == "deny"]


class FakeLLM:
    def __init__(self, outcomes: list[Any] | None = None, role_models: dict | None = None) -> None:
        self.outcomes = list(outcomes or [])
        self.role_models = (
            role_models if role_models is not None else {r: s for r, s in ROLE_MODELS.items()}
        )
        self.totals = UsageTotals()
        self.calls: list[dict[str, Any]] = []

    async def complete(self, role, messages, *, key, schema=None, max_tokens=2048, temperature=0.2):
        override = model_override()
        spec = override or (self.role_models or {}).get(role) or SUPER
        self.calls.append(
            {
                "role": role,
                "messages": messages,
                "model": spec.id,
                "inside": inside_gateway(),
                "max_tokens": max_tokens,
            }
        )
        outcome = self.outcomes.pop(0) if self.outcomes else None
        if isinstance(outcome, BaseException):
            raise outcome
        usage = Usage(model=spec.id, tokens_in=100, tokens_out=20, cost_usd=outcome or 0.001)
        return LLMResponse(role=role, text="ok", usage=usage)


ROLE_MODELS: dict[Role, ModelSpec] = {
    Role.PLANNER: SUPER,
    Role.CODER: LIGHTNING,
    Role.REPAIRER: SUPER,
    Role.ADVERSARY: SUPER,
    Role.JUDGE: SUPER,
    Role.REVIEWER: SUPER,
    Role.NARRATOR: SUPER,
}


class Naps:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=REPO_ROOT / "cases",
    )


@pytest.fixture
def audit() -> Audit:
    return Audit()


@pytest.fixture
def naps() -> Naps:
    return Naps()


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def make_gateway(settings: Settings, audit: Audit, naps: Naps, clock: Clock):
    def build(identity: Any = "mint", **kwargs: Any) -> Gateway:
        real = mint_run_identity(settings, RUN) if identity == "mint" else identity
        loaded = kwargs.pop("loaded", policy_for(settings))
        return Gateway(
            settings,
            RUN,
            real,
            loaded,
            fleet_authorizer(settings, audit=quiet_sandbox_allows(audit)),
            audit,
            sleep=naps,
            rng=lambda: 0.0,
            clock=clock,
            **kwargs,
        )

    return build
