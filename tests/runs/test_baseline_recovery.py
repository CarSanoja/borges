from __future__ import annotations

import pytest

from borges.garden.models import Universe
from borges.runs.baseline_recovery import failing_option, recover_baseline
from tests.analysis.fakes import make_plan


def universe(choices: dict[str, str], status: str, error: str | None = None) -> Universe:
    return Universe(id="u", choices=choices, kind="baseline", status=status, error=error)


async def test_a_failed_default_is_replaced_by_the_next_option_and_said() -> None:
    plan = make_plan()
    default = plan.step("m1").default.id
    seen: list[dict[str, str]] = []

    async def run(choices: dict[str, str]) -> Universe:
        seen.append(choices)
        return universe(choices, "done")

    caveats: list[str] = []
    failed = universe(plan.default_choices(), "failed", f"m1/{default}: exit code -1")
    baseline = await recover_baseline(plan, failed, run, caveats)
    assert baseline.status == "done"
    assert default not in [o.id for o in plan.step("m1").options]
    assert seen[0]["m1"] == plan.step("m1").default.id != default
    assert "failed on the full data (exit code -1)" in caveats[0]


async def test_a_failure_outside_a_decision_default_still_fails_the_run() -> None:
    plan = make_plan()

    async def run(choices: dict[str, str]) -> Universe:
        raise AssertionError("not re-run")

    failed = universe(plan.default_choices(), "failed", "data could not be loaded")
    with pytest.raises(RuntimeError, match="the baseline analysis failed"):
        await recover_baseline(plan, failed, run, [])


def test_only_the_default_of_a_decision_step_is_demoted() -> None:
    plan = make_plan()
    other = next(o.id for o in plan.step("m1").options if not o.is_default)
    assert failing_option(plan, f"m1/{other}: boom") is None
    assert failing_option(plan, f"m1/{plan.step('m1').default.id}: boom") is not None
