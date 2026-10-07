from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from borges.analysis.models import Option, Step
from borges.garden.executor import GardenExecutor
from borges.garden.executor_alone import run_on_root
from borges.sandbox.local_backend import LocalBackend
from tests.analysis.fakes import make_plan

WHOLE = """
import statsmodels.formula.api as smf


def estimate(df, ctx):
    kept = df[df["day"].between(1, 20)]
    fit = smf.ols("y ~ x", data=kept).fit()
    low, high = fit.conf_int().loc["x"]
    return {
        "estimate": float(fit.params["x"]),
        "ci_low": float(low),
        "ci_high": float(high),
        "p_value": float(fit.pvalues["x"]),
        "n": int(fit.nobs),
    }
"""


def step(code: str) -> Step:
    option = Option(id="r1", label="r", rationale="", spec="s", is_default=True, code=code)
    return Step(id="reference", title="t", kind="model", description="d", options=[option])


def data() -> bytes:
    x = [float(i % 7) for i in range(40)]
    frame = pd.DataFrame(
        {"x": x, "y": [2 * v + (i % 3) for i, v in enumerate(x)], "day": range(40)}
    )
    buffer = io.BytesIO()
    frame.to_parquet(buffer)
    return buffer.getvalue()


async def test_a_whole_analysis_runs_on_the_raw_data(tmp_path: Path) -> None:
    plan = make_plan()
    executor = GardenExecutor(LocalBackend(tmp_path), plan, data(), full_data_checks=False)
    await executor.setup()
    result, error = await run_on_root(executor, step(WHOLE))
    assert error is None
    assert result is not None and result.n == 20
    assert abs(result.estimate - 2.0) < 0.2


async def test_a_failing_implementation_reports_its_error(tmp_path: Path) -> None:
    plan = make_plan()
    executor = GardenExecutor(LocalBackend(tmp_path), plan, data(), full_data_checks=False)
    await executor.setup()
    broken = WHOLE.replace('fit.params["x"]', 'fit.params["missing"]')
    result, error = await run_on_root(executor, step(broken))
    assert result is None
    assert error is not None and "missing" in error
