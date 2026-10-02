from __future__ import annotations

from typing import Any

import pytest

from borges.analysis import smoke_core
from borges.analysis.models import Comparator, DecisionRule, Option, Step
from borges.analysis.scale_check import scale_check, scale_instruction
from borges.analysis.smoke_types import SmokeConfig

ODDS = DecisionRule(
    metric="odds ratio of subscribing per additional contact call",
    comparator=Comparator.LT,
    threshold=1.0,
)
LIFT = DecisionRule(metric="conversion lift (percentage points)", threshold=0.0)


def _result(estimate: float, low: float, high: float) -> dict[str, Any]:
    return {"estimate": estimate, "ci_low": low, "ci_high": high, "p_value": 0.01, "n": 100}


def test_log_odds_coefficient_against_an_odds_ratio_rule_fails() -> None:
    check = scale_check(ODDS)
    assert check is not None
    error = check(_result(-0.116, -0.132, -0.0996))
    assert error is not None and "exp(coefficient)" in error


def test_odds_ratio_passes() -> None:
    check = scale_check(ODDS)
    assert check is not None and check(_result(0.89, 0.876, 0.905)) is None


def test_additive_metrics_are_not_checked() -> None:
    assert scale_check(LIFT) is None


def test_instruction_states_the_threshold_and_the_ratio_scale() -> None:
    text = scale_instruction(ODDS)
    assert "compared with 1 (lt)" in text and "exponentiate" in text
    assert "exponentiate" not in scale_instruction(LIFT)


def test_percentage_point_instruction_asks_for_a_proportion() -> None:
    text = scale_instruction(LIFT)
    assert "difference in proportions" in text and "Borges converts units" in text
    assert "exactly that scale" not in text


def make_step() -> tuple[Step, Option]:
    option = Option(id="o", label="l", rationale="r", spec="s", is_default=True, code="x")
    step = Step(id="s", title="t", kind="model", description="d", options=[option])
    return step, option


async def test_smoke_attempt_turns_a_wrong_scale_into_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def execute(config: Any, parent: Any, step: Any, option: Any) -> tuple:
        return "ck", None, None, _result(-0.116, -0.132, -0.0996)

    monkeypatch.setattr(smoke_core, "execute", execute)
    config = SmokeConfig(None, b"", result_check=scale_check(ODDS))  # type: ignore[arg-type]
    step, option = make_step()
    _, error, _, _ = await smoke_core._attempt(config, None, step, option, None)  # type: ignore[arg-type]
    assert error is not None and "log-scale coefficient" in error
