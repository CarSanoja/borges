from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis.harness import parse_error
from tests.analysis.test_harness_design import HEADER, run_model

FIT = """
    import statsmodels.formula.api as smf

    data = df.dropna()
    CALL
    return {"estimate": 0.0, "ci_low": -1.0, "ci_high": 1.0, "p_value": 0.5, "n": len(data)}
"""


@pytest.fixture
def cox_data(tmp_path: Path) -> Path:
    rng = np.random.default_rng(9)
    frame = pd.DataFrame({"treated": rng.integers(0, 2, 200), "age": rng.normal(60, 9, 200)})
    time = rng.exponential(1 / (0.01 * np.exp(-0.5 * frame["treated"])))
    frame["days"] = np.minimum(np.ceil(time), 90)
    frame["event"] = (time <= 90).astype(int)
    frame.to_parquet(tmp_path / "data.parquet")
    return tmp_path


@pytest.mark.parametrize(
    "call",
    [
        'sm.PHReg(data["days"], data["event"], exog=data[["treated"]]).fit()',
        'smf.phreg("days ~ treated", data, status=data["event"]).fit(cov_type="HC1")',
    ],
)
def test_a_wrong_phreg_call_is_told_how_phreg_is_called(cox_data: Path, call: str) -> None:
    done = run_model(cox_data, HEADER + FIT.replace("CALL", call))
    error = parse_error(done.stdout)
    assert done.returncode == 1 and error is not None
    assert "the event always as status=" in error and ".fit(groups=np.arange(len(data)))" in error


def test_an_unrelated_error_gets_no_phreg_hint(cox_data: Path) -> None:
    done = run_model(cox_data, HEADER + FIT.replace("CALL", 'data["missing_column"]'))
    error = parse_error(done.stdout)
    assert error is not None and "status=" not in error
