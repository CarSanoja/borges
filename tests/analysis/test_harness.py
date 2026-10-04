from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from borges.analysis.harness import (
    parse_error,
    parse_output,
    render_step,
    step_command,
    step_filename,
)
from borges.analysis.models import Option, Step

FILTER_CODE = """
def apply(df, ctx):
    ctx["arm_col"] = "arm"
    return df[df["age"] >= 18].copy()
"""

MODEL_CODE = """
import math
from scipy import stats


def estimate(df, ctx):
    a = df[df[ctx["arm_col"]] == "treat"]["y"]
    b = df[df[ctx["arm_col"]] == "ctrl"]["y"]
    p1, p0 = a.mean(), b.mean()
    se = math.sqrt(p1 * (1 - p1) / len(a) + p0 * (1 - p0) / len(b))
    diff = p1 - p0
    z = diff / se
    return {
        "estimate": float(diff),
        "ci_low": float(diff - 1.96 * se),
        "ci_high": float(diff + 1.96 * se),
        "p_value": float(2 * (1 - stats.norm.cdf(abs(z)))),
        "n": len(df),
        "extra": {"z": float(z)},
    }
"""


def make_step(step_id: str, kind: str, code: str | None, option_id: str = "o1") -> tuple:
    option = Option(id=option_id, label="l", rationale="r", spec="s", is_default=True, code=code)
    step = Step(id=step_id, title="t", kind=kind, description="d", options=[option])
    return step, option


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        {
            "age": [10, 20, 30, 40, 50, 60, 70, 80, 17, 25],
            "arm": ["treat", "ctrl"] * 5,
            "y": [1, 0, 1, 1, 0, 0, 1, 0, 1, 1],
        }
    )
    df.to_parquet(tmp_path / "data.parquet")
    return tmp_path


def run(workdir: Path, step: Step, option: Option) -> subprocess.CompletedProcess[str]:
    path = workdir / step_filename(step.id, option.id)
    path.parent.mkdir(exist_ok=True)
    path.write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, str(path)], cwd=workdir, capture_output=True, text=True, timeout=120
    )


def test_step_filename_sanitises() -> None:
    assert step_filename("s 1", "a/b.c") == "steps/s_1__a_b_c.py"
    assert step_filename("s1", "o-2_x") == "steps/s1__o-2_x.py"


def test_step_command() -> None:
    assert step_command("s1", "o1") == ["python", "steps/s1__o1.py"]


def test_render_requires_code() -> None:
    step, option = make_step("s1", "filter", None)
    with pytest.raises(ValueError):
        render_step(step, option)


def test_render_embeds_code_verbatim() -> None:
    step, option = make_step("s1", "filter", FILTER_CODE)
    assert FILTER_CODE.strip() in render_step(step, option)


def test_filter_then_model_carries_state(workdir: Path) -> None:
    fstep, fopt = make_step("s1", "filter", FILTER_CODE)
    first = run(workdir, fstep, fopt)
    assert first.returncode == 0, first.stdout + first.stderr
    traces, result = parse_output(first.stdout)
    assert result is None
    assert (traces[0].rows_before, traces[0].rows_after) == (10, 8)
    assert (workdir / "state" / "ctx.json").exists()

    mstep, mopt = make_step("s2", "model", MODEL_CODE)
    second = run(workdir, mstep, mopt)
    assert second.returncode == 0, second.stdout + second.stderr
    traces, result = parse_output(second.stdout)
    assert traces[0].step_id == "s2"
    assert traces[0].rows_before == 8
    assert result is not None
    assert result.n == 8
    assert result.ci_low <= result.estimate <= result.ci_high
    assert 0 <= result.p_value <= 1
    assert "z" in result.extra
    assert parse_error(second.stdout) is None


def test_model_without_prior_state_uses_root_data(workdir: Path) -> None:
    code = MODEL_CODE.replace('ctx["arm_col"]', '"arm"')
    step, option = make_step("s1", "model", code)
    proc = run(workdir, step, option)
    _, result = parse_output(proc.stdout)
    assert proc.returncode == 0
    assert result is not None and result.n == 10


def test_exception_surfaces_as_error(workdir: Path) -> None:
    code = "def apply(df, ctx):\n    return df['missing']\n"
    step, option = make_step("s1", "filter", code)
    proc = run(workdir, step, option)
    assert proc.returncode == 1
    message = parse_error(proc.stdout)
    assert message is not None and "KeyError" in message
    assert not (workdir / "state" / "df.parquet").exists()


def test_apply_must_return_dataframe(workdir: Path) -> None:
    step, option = make_step("s1", "filter", "def apply(df, ctx):\n    return 3\n")
    proc = run(workdir, step, option)
    assert proc.returncode == 1
    assert "DataFrame" in (parse_error(proc.stdout) or "")


@pytest.mark.parametrize(
    "payload",
    [
        '{"estimate": 1.0, "ci_low": 0.0, "ci_high": 2.0, "p_value": 1.5, "n": 3}',
        '{"estimate": 1.0, "ci_low": 3.0, "ci_high": 2.0, "p_value": 0.5, "n": 3}',
        '{"estimate": float("nan"), "ci_low": 0.0, "ci_high": 2.0, "p_value": 0.5, "n": 3}',
        '{"estimate": 1.0, "ci_low": 0.0, "ci_high": 2.0, "p_value": 0.5}',
        "[1, 2]",
    ],
)
def test_invalid_model_result_rejected(workdir: Path, payload: str) -> None:
    step, option = make_step("s1", "model", f"def estimate(df, ctx):\n    return {payload}\n")
    proc = run(workdir, step, option)
    assert proc.returncode == 1
    assert parse_error(proc.stdout) is not None
    assert parse_output(proc.stdout)[1] is None


def test_parse_output_ignores_unrelated_lines() -> None:
    stdout = (
        "hello\n"
        'BORGES_TRACE {"step_id": "a", "option_id": "b", "rows_before": 2, "rows_after": 1,'
        ' "note": ""}\n'
        "BORGES_TRACE not json\n"
        "noise\n"
    )
    traces, result = parse_output(stdout)
    assert len(traces) == 1 and result is None
    assert parse_error(stdout) is None


def test_system_exit_from_user_code_is_an_error(workdir: Path) -> None:
    step, option = make_step("s1", "filter", "def apply(df, ctx):\n    raise SystemExit(0)\n")
    proc = run(workdir, step, option)
    assert proc.returncode == 1
    assert "SystemExit" in (parse_error(proc.stdout) or "")


def test_numpy_scalars_are_accepted_in_results(workdir: Path) -> None:
    code = (
        "import numpy as np\n\n\n"
        "def estimate(df, ctx):\n"
        "    return {'estimate': np.float32(0.5), 'ci_low': np.float32(0.25), "
        "'ci_high': np.float64(1.0), 'p_value': np.float32(0.5), "
        "'n': df['y'].sum(), 'extra': {'k': np.int64(3)}}\n"
    )
    step, option = make_step("s1", "model", code)
    proc = run(workdir, step, option)
    _, result = parse_output(proc.stdout)
    assert proc.returncode == 0
    assert result is not None and result.n == 6 and result.extra == {"k": 3.0}


def test_numpy_bool_is_not_a_number(workdir: Path) -> None:
    code = (
        "import numpy as np\n\n\n"
        "def estimate(df, ctx):\n"
        "    return {'estimate': np.bool_(True), 'ci_low': 0.0, 'ci_high': 1.0, "
        "'p_value': 0.5, 'n': 3}\n"
    )
    step, option = make_step("s1", "model", code)
    proc = run(workdir, step, option)
    assert proc.returncode == 1


def test_traceback_and_message_carry_no_working_directory(workdir: Path) -> None:
    code = (
        "import warnings\n\n\n"
        "def apply(df, ctx):\n"
        "    warnings.warn('harmless')\n"
        "    raise ValueError('cannot read ' + 'x')\n"
    )
    step, option = make_step("s1", "filter", code)
    proc = run(workdir, step, option)
    message = parse_error(proc.stdout)
    assert message is not None and "ValueError: cannot read x" in message
    assert str(workdir) not in message
    assert str(workdir.resolve()) not in message


def test_error_from_inside_a_library_carries_no_host_paths(workdir: Path) -> None:
    code = "def apply(df, ctx):\n    return df.merge(df, on='nope')\n"
    step, option = make_step("s1", "filter", code)
    proc = run(workdir, step, option)
    message = parse_error(proc.stdout)
    assert message is not None and "KeyError" in message
    for marker in ("/Users/", "/home/", ".venv", str(Path(sys.prefix))):
        assert marker not in message
    assert "site-packages/pandas" in message


def test_a_model_note_reaches_the_trace(workdir: Path) -> None:
    code = (
        "def estimate(df, ctx):\n"
        "    return {'estimate': 1.0, 'ci_low': 0.5, 'ci_high': 1.5, 'p_value': 0.1, 'n': 10,"
        " 'note': 'aliased covariates dropped: z'}\n"
    )
    step, option = make_step("s1", "model", code)
    proc = run(workdir, step, option)
    traces, result = parse_output(proc.stdout)
    assert proc.returncode == 0 and result is not None
    assert traces[0].note == "aliased covariates dropped: z"


GLM_CODE = """
import numpy as np
import statsmodels.api as sm


def estimate(df, ctx):
    y = (df["age"] > df["age"].median()).astype(float)
    x = df[["age"]].astype(float)
    __CONST__
    fit = sm.GLM(y, x, family=sm.families.Poisson()).fit()
    low, high = fit.conf_int().loc["age"]
    return {"estimate": float(fit.params["age"]), "ci_low": float(low),
            "ci_high": float(high), "p_value": float(fit.pvalues["age"]), "n": int(len(df))}
"""


def test_a_model_without_an_intercept_fails_with_a_clear_reason(workdir: Path) -> None:
    step, option = make_step("s1", "model", GLM_CODE.replace("__CONST__", "pass"))
    proc = run(workdir, step, option)
    assert proc.returncode != 0
    assert "has no intercept" in (parse_error(proc.stdout) or "")


def test_a_model_with_an_intercept_passes_the_check(workdir: Path) -> None:
    code = GLM_CODE.replace("__CONST__", "x = sm.add_constant(x, has_constant='add')")
    step, option = make_step("s1", "model", code)
    proc = run(workdir, step, option)
    assert "has no intercept" not in (parse_error(proc.stdout) or "")
