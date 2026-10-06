from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd
from pandas.api import types as pdt

from borges.analysis.models import RepeatedUnit

MIN_UNITS = 30
MIN_ROWS_PER_UNIT = 2.0
SNAKE_ID = re.compile(r"(?:^|_)(?:id|code|num|key)$", re.IGNORECASE)
CAMEL_ID = re.compile(r"[a-z0-9](?:Id|ID|Num|Code|Short|Key)$")


def looks_like_identifier(name: str) -> bool:
    return SNAKE_ID.search(name) is not None or CAMEL_ID.search(name) is not None


def _keyable(series: pd.Series) -> bool:
    if pdt.is_bool_dtype(series):
        return False
    if pdt.is_float_dtype(series):
        values = series.dropna()
        return bool((values % 1 == 0).all())
    return pdt.is_integer_dtype(series) or not pdt.is_numeric_dtype(series)


def _same_grouping(frame: pd.DataFrame, first: str, second: str) -> bool:
    pairs = frame[[first, second]].dropna().drop_duplicates()
    return len(pairs) == pairs[first].nunique() == pairs[second].nunique()


def detect_repeated_units(df: pd.DataFrame, exclude: Iterable[str] = ()) -> list[RepeatedUnit]:
    """Identifier columns whose values repeat across rows: the units that make rows dependent.

    A column is a repeated unit when all of these hold: its name reads as an identifier (ends in
    id, code, num, key, short, in snake_case or camelCase); its values are integers or text, not
    fractions or booleans; it has at least 30 distinct non-missing values; and its non-missing
    rows average at least 2 per value. The outcome and the exposure, passed as `exclude`, are
    never units. A column that groups the rows exactly as an earlier detected column does (a
    player name beside its code) is the same unit and is left out. Units come back in column
    order with their distinct count and the mean rows per value.
    """
    skip = set(exclude)
    found: list[RepeatedUnit] = []
    for column in df.columns:
        name = str(column)
        if name in skip or not looks_like_identifier(name) or not _keyable(df[column]):
            continue
        present = int(df[column].notna().sum())
        distinct = int(df[column].nunique(dropna=True))
        if distinct < MIN_UNITS or present / distinct < MIN_ROWS_PER_UNIT:
            continue
        if any(_same_grouping(df, unit.name, name) for unit in found):
            continue
        found.append(
            RepeatedUnit(name=name, n_units=distinct, rows_per_unit=round(present / distinct, 2))
        )
    return found
