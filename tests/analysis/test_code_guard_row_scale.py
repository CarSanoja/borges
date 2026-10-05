from __future__ import annotations

import pytest

from borges.analysis.code_guard_row_scale import row_scale_violations

ROWWISE = """import numpy as np

def apply(df, ctx):
    mat = df[["a", "b", "c"]].values.astype(float)
    means = mat.mean(axis=1, keepdims=True)
    stds = mat.std(axis=1, keepdims=True, ddof=0)
    stds = np.where(stds == 0, 1.0, stds)
    z = (mat - means) / stds
    df["s"] = z[:, 0]
    return df
"""


def test_the_marp_rowwise_z_score_is_flagged() -> None:
    [problem] = row_scale_violations(ROWWISE)
    assert problem.startswith("line 8: the code divides by a standard deviation taken across")


def test_a_direct_rowwise_division_is_flagged() -> None:
    code = (
        "def apply(df, ctx):\n    z = df[['a', 'b']] / df[['a', 'b']].std(axis=1)\n    return df\n"
    )
    assert row_scale_violations(code)


@pytest.mark.parametrize(
    "line",
    [
        "z = (items - items.mean()) / items.std(ddof=0)",
        "z = (items - items.mean(axis=0)) / items.std(axis=0)",
        "z = items.mean(axis=1) / 9",
    ],
)
def test_column_scaling_and_row_means_pass(line: str) -> None:
    code = f"def apply(df, ctx):\n    items = df[['a', 'b']]\n    {line}\n    return df\n"
    assert row_scale_violations(code) == []
