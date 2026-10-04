from __future__ import annotations

import pytest

from borges.analysis.code_guard import check_code

HEADER = "import numpy as np\nimport pandas as pd\n\n\n"


def apply(body: str) -> str:
    return HEADER + "def apply(df, ctx):\n" + body + "    return df\n"


@pytest.mark.parametrize(
    ("call", "safe"),
    [
        ("np.median(df['skin_tone'])", "np.nanmedian"),
        ("np.percentile(df['games'], 99)", "np.nanpercentile"),
        ("np.quantile(df['games'], 0.99)", "np.nanquantile"),
    ],
)
def test_a_nan_blind_threshold_in_a_data_step_is_refused(call: str, safe: str) -> None:
    code = apply(f"    cut = {call}\n    df['dark'] = (df['skin_tone'] >= cut).astype(int)\n")
    violations = check_code(code, "transform")
    assert len(violations) == 1 and "returns NaN" in violations[0] and safe in violations[0]


def test_pandas_and_nan_safe_thresholds_pass() -> None:
    body = (
        "    cut = df['skin_tone'].median()\n"
        "    top = np.nanquantile(df['games'], 0.99)\n"
        "    df['dark'] = (df['skin_tone'] >= cut).astype(int)\n"
    )
    assert check_code(apply(body), "transform") == []


def test_a_model_step_may_take_percentiles_of_its_own_draws() -> None:
    code = (
        HEADER
        + "def estimate(df, ctx):\n"
        + "    draws = np.array([1.0, 2.0, 3.0])\n"
        + "    low, high = np.percentile(draws, [2.5, 97.5])\n"
        + "    return {'estimate': 2.0, 'ci_low': low, 'ci_high': high, 'p_value': 0.5, 'n': 3}\n"
    )
    assert check_code(code, "model") == []
