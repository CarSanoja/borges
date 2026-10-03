from __future__ import annotations

import json
from collections.abc import Mapping

import pandas as pd
from pandas.api import types as pdt

from borges.analysis.models import ColumnProfile, DatasetProfile

TOP_VALUES = 5


def _round(value: float) -> float:
    return round(float(value), 4)


def _numeric_summary(series: pd.Series) -> dict[str, float | str]:
    values = series.dropna().astype(float)
    if values.empty:
        return {}
    return {
        "mean": _round(values.mean()),
        "std": _round(values.std()) if len(values) > 1 else 0.0,
        "min": _round(values.min()),
        "p50": _round(values.median()),
        "max": _round(values.max()),
    }


def _bool_summary(series: pd.Series) -> dict[str, float | str]:
    values = series.dropna()
    if values.empty:
        return {}
    return {"share_true": _round(values.astype(bool).mean())}


def _categorical_summary(series: pd.Series) -> dict[str, float | str]:
    counts = series.astype(str)[series.notna()].value_counts().head(TOP_VALUES)
    return {f"top_{i + 1}": f"{value}: {count}" for i, (value, count) in enumerate(counts.items())}


def _summary(series: pd.Series) -> dict[str, float | str]:
    if pdt.is_bool_dtype(series):
        return _bool_summary(series)
    if pdt.is_numeric_dtype(series):
        return _numeric_summary(series)
    return _categorical_summary(series)


def _profile_column(series: pd.Series, name: str, note: str | None = None) -> ColumnProfile:
    return ColumnProfile(
        name=name,
        dtype=str(series.dtype),
        n_missing=int(series.isna().sum()),
        n_unique=int(series.nunique(dropna=True)),
        summary=_summary(series),
        note=note,
    )


def _sample_rows(df: pd.DataFrame, sample: int) -> list[dict[str, object]]:
    head = df.head(max(sample, 0))
    payload = head.to_json(orient="records", date_format="iso", default_handler=str)
    rows: list[dict[str, object]] = json.loads(payload)
    return rows


def profile_dataframe(
    df: pd.DataFrame,
    name: str,
    sample: int = 5,
    column_notes: Mapping[str, str] | None = None,
) -> DatasetProfile:
    notes = column_notes or {}
    columns = [_profile_column(df[col], str(col), notes.get(str(col))) for col in df.columns]
    return DatasetProfile(
        name=name,
        n_rows=int(len(df)),
        columns=columns,
        sample_rows=_sample_rows(df, sample),
    )


def blind_profile(profile: DatasetProfile) -> DatasetProfile:
    """The profile as the agents see it in blind mode: no column notes or value descriptions."""
    return profile.model_copy(
        update={"columns": [c.model_copy(update={"note": None}) for c in profile.columns]}
    )
