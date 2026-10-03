from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

from borges.analysis.coder import code_plan
from borges.analysis.coder_smoke import SmokeConfig
from borges.analysis.models import AnalysisPlan
from borges.analysis.prompts.coder import ALLOWLIST, SYSTEM, build_messages
from borges.analysis.schemas import CoderOutput
from borges.llm.client import (
    DEFAULT_ROLE_MODELS,
    NANO,
    SUPER,
    LLMError,
    LLMResponse,
    Role,
    Usage,
)
from borges.sandbox.local_backend import LocalBackend
from tests.analysis.fakes import make_plan

KEEP = "def apply(df, ctx):\n    return df.copy()"
SKLEARN = (
    "from sklearn.linear_model import LinearRegression\n\ndef estimate(df, ctx):\n    return {}"
)
GOOD = (
    "def estimate(df, ctx):\n"
    '    m = float(df["outcome"].mean())\n'
    '    return {"estimate": m, "ci_low": m - 1.0, "ci_high": m + 1.0, "p_value": 0.5, '
    '"n": len(df)}'
)
NO_N = (
    "def estimate(df, ctx):\n"
    '    m = float(df["outcome"].mean())\n'
    '    return {"estimate": m, "ci_low": m - 1.0, "ci_high": m + 1.0, "p_value": 0.5}'
)
TOKENS_IN, TOKENS_OUT = 1000, 500


@dataclass
class PricedLLM:
    responses: dict[str, str]
    calls: list[tuple[Role, str, str]] = field(default_factory=list)
    spent: float = 0.0

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
        spec = DEFAULT_ROLE_MODELS[role]
        self.calls.append((role, key, messages[1]["content"]))
        cost = spec.cost(TOKENS_IN, TOKENS_OUT)
        self.spent += cost
        usage = Usage(model=spec.id, tokens_in=TOKENS_IN, tokens_out=TOKENS_OUT, cost_usd=cost)
        parsed: dict[str, Any] = CoderOutput(code=self.responses[key]).model_dump()
        return LLMResponse(role=role, text="", parsed=parsed, usage=usage)


def plan_with_welch_only() -> AnalysisPlan:
    plan = make_plan(with_code=True)
    step = plan.step("m1")
    step.options = [o for o in step.options if o.id == "ols"]
    step.option("ols").code = None
    plan.step("d1").options = [plan.step("d1").option("keep")]
    return plan


def dataset() -> bytes:
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"group": ["a", "b"] * 150, "outcome": rng.normal(size=300)})
    buffer = io.BytesIO()
    frame.to_parquet(buffer)
    return buffer.getvalue()


async def test_guard_violation_is_repaired_by_super_and_recorded() -> None:
    llm = PricedLLM({"coder:m1.ols": SKLEARN, "coder:m1.ols:repair": GOOD})
    events: list[tuple] = []

    async def on_coded(*args: Any) -> None:
        events.append(args)

    coded = await code_plan(llm, plan_with_welch_only(), on_coded=on_coded)
    assert coded.step("m1").option("ols").code == GOOD
    assert [c[0] for c in llm.calls] == [Role.CODER, Role.REPAIRER]
    assert events == [("m1", "ols", True, 2, None, [NANO.id, SUPER.id])]
    repair_prompt = llm.calls[1][2]
    assert "sklearn is not available; use statsmodels or numpy" in repair_prompt
    assert ALLOWLIST in repair_prompt and "statsmodels.formula.api" in ALLOWLIST


async def test_smoke_failure_for_a_missing_key_is_repaired_by_super(tmp_path: Path) -> None:
    llm = PricedLLM({"coder:m1.ols": NO_N, "coder:m1.ols:smoke1": GOOD})
    smoke_events: list[tuple] = []

    async def on_smoke(*args: Any) -> None:
        smoke_events.append(args)

    coded_events: list[tuple] = []

    async def on_coded(*args: Any) -> None:
        coded_events.append(args)

    config = SmokeConfig(LocalBackend(tmp_path), dataset(), on_smoke)
    coded = await code_plan(llm, plan_with_welch_only(), on_coded, smoke=config)
    assert coded.step("m1").option("ols").code == GOOD
    assert [c[0] for c in llm.calls] == [Role.CODER, Role.REPAIRER]
    assert coded_events == [("m1", "ols", True, 1, None, [NANO.id])]
    model_smoke = next(e for e in smoke_events if e[0] == "m1")
    assert model_smoke[2:] == ("repaired", 2, None, [SUPER.id])
    prompt = llm.calls[1][2]
    assert (
        "missing key 'n'" in prompt and '"estimate", "ci_low", "ci_high", "p_value", "n"' in prompt
    )


async def test_costs_use_each_models_own_prices() -> None:
    llm = PricedLLM({"coder:m1.ols": SKLEARN, "coder:m1.ols:repair": GOOD})
    await code_plan(llm, plan_with_welch_only())
    expected = NANO.cost(TOKENS_IN, TOKENS_OUT) + SUPER.cost(TOKENS_IN, TOKENS_OUT)
    assert abs(llm.spent - expected) < 1e-12
    assert SUPER.cost(TOKENS_IN, TOKENS_OUT) > NANO.cost(TOKENS_IN, TOKENS_OUT)


def test_repairer_role_maps_to_the_planner_model() -> None:
    assert DEFAULT_ROLE_MODELS[Role.REPAIRER] is DEFAULT_ROLE_MODELS[Role.PLANNER] is SUPER


def test_first_attempt_uses_coder_role_and_prompt_states_the_contract() -> None:
    plan = plan_with_welch_only()
    step = plan.step("m1")
    first = build_messages(plan, step, step.option("ols"), None)
    text = first[1]["content"]
    assert '"estimate", "ci_low", "ci_high", "p_value", "n"' in text
    assert "statsmodels.formula.api" in text and "statsmodels.formula.api" in SYSTEM
    assert "sklearn" not in text
    filter_step = plan.step("d1")
    assert (
        "def apply(df, ctx)"
        in build_messages(plan, filter_step, filter_step.option("keep"), None)[1]["content"]
    )


async def test_repair_failure_still_raises_when_super_also_violates() -> None:
    llm = PricedLLM(
        {
            "coder:m1.ols": SKLEARN,
            "coder:m1.ols:repair": SKLEARN,
            "coder:m1.ols:guard_recode": SKLEARN,
        }
    )
    try:
        await code_plan(llm, plan_with_welch_only())
    except LLMError as exc:
        assert "violates the guard" in str(exc) or "failed coding" in str(exc)
    else:
        raise AssertionError("expected LLMError")
