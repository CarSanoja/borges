from __future__ import annotations

import pytest

from borges.analysis.harness import RESULT_KEYS, parse_error, parse_output
from tests.analysis.test_harness import make_step, run, workdir  # noqa: F401


def payload(**overrides: object) -> str:
    base = {"estimate": 0.5, "ci_low": 0.2, "ci_high": 0.8, "p_value": 0.04, "n": 10}
    return repr({**base, **overrides})


def outcome(workdir, body: str) -> tuple[str | None, bool]:  # noqa: F811
    step, option = make_step("s1", "model", f"def estimate(df, ctx):\n    return {body}\n")
    proc = run(workdir, step, option)
    return parse_error(proc.stdout), parse_output(proc.stdout)[1] is not None


def test_result_keys_are_the_contract() -> None:
    assert RESULT_KEYS == ("estimate", "ci_low", "ci_high", "p_value", "n")


def test_degenerate_interval_not_containing_the_estimate(workdir) -> None:  # noqa: F811
    error, accepted = outcome(
        workdir, payload(estimate=0.5286, ci_low=0.3603, ci_high=0.3603, p_value=0.0, n=500)
    )
    assert not accepted
    assert (
        "the 95% interval [0.3603, 0.3603] is degenerate and does not contain the estimate 0.5286"
        in (error or "")
    )


def test_degenerate_interval_around_the_estimate_is_still_rejected(workdir) -> None:  # noqa: F811
    error, accepted = outcome(workdir, payload(estimate=0.4, ci_low=0.4, ci_high=0.4))
    assert not accepted
    assert "[0.4, 0.4] is degenerate" in (error or "")
    assert "does not contain" not in (error or "")


def test_inverted_interval(workdir) -> None:  # noqa: F811
    error, accepted = outcome(workdir, payload(ci_low=0.9, ci_high=0.1, estimate=0.5))
    assert not accepted and "is inverted" in (error or "")


def test_estimate_outside_interval(workdir) -> None:  # noqa: F811
    error, accepted = outcome(workdir, payload(estimate=0.95))
    assert not accepted
    assert "the 95% interval [0.2, 0.8] does not contain the estimate 0.95" in (error or "")


def test_estimate_on_the_edge_within_tolerance_is_accepted(workdir) -> None:  # noqa: F811
    _, accepted = outcome(workdir, payload(estimate=0.8 + 1e-9))
    assert accepted


@pytest.mark.parametrize("p_value", [1.2, -0.01])
def test_p_value_outside_unit_interval(workdir, p_value: float) -> None:  # noqa: F811
    error, accepted = outcome(workdir, payload(p_value=p_value))
    assert not accepted and "is outside the range [0, 1]" in (error or "")


@pytest.mark.parametrize("n", [0, -3, 12.5])
def test_n_must_be_a_positive_integer(workdir, n: float) -> None:  # noqa: F811
    error, accepted = outcome(workdir, payload(n=n))
    assert not accepted and "n must be a positive integer" in (error or "")


def test_integral_float_n_and_zero_p_value_are_accepted(workdir) -> None:  # noqa: F811
    _, accepted = outcome(workdir, payload(n=40.0, p_value=0.0))
    assert accepted
