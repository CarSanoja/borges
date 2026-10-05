from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis.harness import parse_error, parse_output, render_step
from borges.analysis.models import Option, Step

DUMMIFY_ALL = """
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def estimate(df, ctx):
    covariates = list(ctx.get("covariates", []))
    dummies = pd.get_dummies(df, drop_first=True, dtype=float)
    keep = [c for c in ["y", "x", *covariates] if c in dummies.columns]
    rhs = [c for c in ["x", *covariates] if c in keep]
    fit = smf.ols("y ~ " + " + ".join(rhs), data=dummies[keep]).fit()
    ci = fit.conf_int().loc["x"]
    return {"estimate": float(fit.params["x"]), "ci_low": float(ci[0]),
            "ci_high": float(ci[1]), "p_value": float(fit.pvalues["x"]), "n": int(fit.nobs)}
"""

FORMULA = DUMMIFY_ALL.replace(
    'fit = smf.ols("y ~ " + " + ".join(rhs), data=dummies[keep]).fit()',
    'fit = smf.ols("y ~ x + " + " + ".join(f"C({c})" for c in covariates), data=df).fit()',
)


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"x": rng.normal(size=120), "job": ["a", "b", "c"] * 40})
    frame["y"] = 0.5 * frame["x"] + rng.normal(size=120)
    frame.to_parquet(tmp_path / "data.parquet")
    (tmp_path / "state").mkdir()
    frame.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({"covariates": ["job"]}))
    return tmp_path


def run(workdir: Path, code: str, label: str = "OLS adjusted") -> subprocess.CompletedProcess:
    option = Option(id="o", label=label, rationale="r", spec="s", is_default=True, code=code)
    step = Step(id="model", title="t", kind="model", description="d", options=[option])
    path = workdir / "step.py"
    path.write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, str(path)], cwd=workdir, capture_output=True, text=True, timeout=120
    )


def test_a_model_that_drops_a_listed_categorical_covariate_fails(workdir: Path) -> None:
    done = run(workdir, DUMMIFY_ALL)
    assert done.returncode == 1
    error = parse_error(done.stdout) or ""
    assert "ctx['covariates'] lists job, but no term of the fitted model" in error


def test_a_model_that_fits_the_listed_covariate_passes(workdir: Path) -> None:
    done = run(workdir, FORMULA)
    assert done.returncode == 0, done.stdout
    traces, _ = parse_output(done.stdout)
    assert traces[0].design is not None and "job" in traces[0].design["terms"]


def test_an_option_that_says_it_uses_no_covariates_is_not_checked(workdir: Path) -> None:
    done = run(workdir, DUMMIFY_ALL, label="OLS without covariates")
    assert done.returncode == 0, done.stdout


def test_a_covariate_with_one_value_in_the_frame_is_not_required(workdir: Path) -> None:
    frame = pd.read_parquet(workdir / "state" / "df.parquet").assign(job="MISSING")
    frame.to_parquet(workdir / "state" / "df.parquet")
    done = run(workdir, DUMMIFY_ALL)
    assert done.returncode == 0, done.stdout


LEVEL_NAMED = """
import numpy as np
import pandas as pd
import statsmodels.api as sm


def estimate(df, ctx):
    dummies = pd.get_dummies(df["job"], drop_first=True, dtype=float)
    exog = sm.add_constant(pd.concat([df[["x"]], dummies], axis=1))
    fit = sm.OLS(df["y"], exog).fit()
    ci = fit.conf_int().loc["x"]
    return {"estimate": float(fit.params["x"]), "ci_low": float(ci[0]),
            "ci_high": float(ci[1]), "p_value": float(fit.pvalues["x"]), "n": int(fit.nobs)}
"""


def test_dummies_named_by_the_levels_of_the_covariate_count_as_adjusting_for_it(
    workdir: Path,
) -> None:
    done = run(workdir, LEVEL_NAMED)
    assert done.returncode == 0, done.stdout
    dropped = LEVEL_NAMED.replace('pd.concat([df[["x"]], dummies], axis=1)', 'df[["x"]]')
    assert run(workdir, dropped).returncode == 1
