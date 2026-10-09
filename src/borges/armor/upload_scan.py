from __future__ import annotations

from collections import Counter

import pandas as pd
from pandas.api import types as pdt
from pydantic import BaseModel, Field

from borges.armor.pii import find_pii
from borges.armor.pii_names import PERSON_NAME_KIND, is_name_header, values_look_like_names

SCAN_VALUES_PER_COLUMN = 2000
LONG_NUMBER = 10**12


class PiiColumn(BaseModel):
    column: str
    kinds: dict[str, int]
    scanned: int
    total_rows: int


class PiiSummary(BaseModel):
    columns: list[PiiColumn] = Field(default_factory=list)
    total_detections: int = 0
    note: str = (
        "Counts come from a sample of each column and never include values. Models see "
        "redacted tokens; your analysis code still reads the raw columns."
    )


def _sample(series: pd.Series) -> list[str]:
    values = series.dropna()
    if values.empty:
        return []
    if len(values) > SCAN_VALUES_PER_COLUMN:
        step = len(values) / SCAN_VALUES_PER_COLUMN
        values = values.iloc[[int(i * step) for i in range(SCAN_VALUES_PER_COLUMN)]]
    return [str(v) for v in values]


def _scannable(series: pd.Series) -> bool:
    if pdt.is_bool_dtype(series):
        return False
    if pdt.is_numeric_dtype(series):
        return pdt.is_integer_dtype(series) and bool((series.dropna().abs() >= LONG_NUMBER).any())
    return True


def scan_column(series: pd.Series, name: str) -> PiiColumn | None:
    if not _scannable(series):
        return None
    sampled = _sample(series)
    kinds: Counter[str] = Counter()
    names = is_name_header(name) or values_look_like_names(
        sampled, int(series.nunique(dropna=True)), len(series)
    )
    for text in sampled:
        found = find_pii(text, name)
        kinds.update(match.kind for match in found)
        if names and not found and text.strip():
            kinds[PERSON_NAME_KIND] += 1
    if not kinds:
        return None
    return PiiColumn(
        column=name, kinds=dict(sorted(kinds.items())), scanned=len(sampled), total_rows=len(series)
    )


def scan_dataframe(df: pd.DataFrame) -> PiiSummary:
    columns = [c for c in (scan_column(df[col], str(col)) for col in df.columns) if c is not None]
    total = sum(sum(c.kinds.values()) for c in columns)
    return PiiSummary(columns=columns, total_detections=total)
