from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.analysis.code_guard import check_code
from tests.analysis.test_code_guard_rows import model, row_errors

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "body",
    [
        "t = df[df['variant'] == 'treatment']\nc = df[df['variant'] == 'control']\nreturn {}",
        "a = df[df.skin == 'dark'].copy()\nb = df[df.skin == 'light'].copy()\nreturn {}",
        "y = df['converted']\nt = df['variant']\nm = y[t == 'treatment'].mean()\nreturn {}",
        "m = df['y'][df['t'] == 1].mean()\nreturn {}",
    ],
)
def test_two_group_contrasts_and_column_series_are_accepted(body: str) -> None:
    assert row_errors(body) == []


@pytest.mark.parametrize(
    "body",
    [
        "sub = df[df['variant'] == 'treatment']\nreturn {}",
        "df = df[df['a'] == 1]\nreturn {}",
        "df = df[df['a'] == 1]\nother = df[df['a'] == 2]\nreturn {}",
        "d = df.loc[lambda t: t['x'] > 0]\nreturn {}",
        "d = df[(df['x'] > 0).values]\nreturn {}",
        "d = df.where(df['x'] > 0).dropna()\nreturn {}",
        "d = df.groupby('u').filter(lambda g: len(g) > 1)\nreturn {}",
    ],
)
def test_single_selections_and_extra_row_filter_forms_are_rejected(body: str) -> None:
    assert row_errors(body)


def test_numpy_where_is_not_a_row_filter() -> None:
    assert row_errors("g = np.where(df['x'] > 0, 1, 0)\nreturn {}") == []


def test_committed_live_checkout_model_code_is_accepted() -> None:
    path = ROOT / "cases/checkout_ab/recorded-live/events.jsonl"
    codes = [
        text
        for line in path.read_text().splitlines()
        for text in _strings(json.loads(line))
        if "def estimate" in text
    ]
    assert codes
    for code in codes:
        assert [v for v in check_code(code, "model") if "row filter" in v] == []


def _strings(value: object) -> list[str]:
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return [value] if isinstance(value, str) else []


def test_model_helper_builds_a_valid_function() -> None:
    assert "def estimate" in model("return {}")
