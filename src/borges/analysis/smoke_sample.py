from __future__ import annotations

import re

import numpy as np
import pandas as pd

ID_NAME = re.compile(r"(?:^|_)id$", re.IGNORECASE)
MIN_GROUPS = 20
COVER_MAX_LEVELS = 50
RARE_MIN = 20


def group_column(frame: pd.DataFrame) -> str | None:
    """An id column whose values repeat, such as sessions per user; None when there is none."""
    best: tuple[float, str] | None = None
    for column in frame.columns:
        name = str(column)
        if not ID_NAME.search(name) or pd.api.types.is_float_dtype(frame[column]):
            continue
        groups = int(frame[column].nunique(dropna=True))
        if groups < MIN_GROUPS or groups >= len(frame):
            continue
        size = len(frame) / groups
        if best is None or size < best[0]:
            best = (size, name)
    return None if best is None else best[1]


def _is_label(series: pd.Series) -> bool:
    return (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
        or pd.api.types.is_bool_dtype(series)
        or isinstance(series.dtype, pd.CategoricalDtype)
    )


def missing_levels(frame: pd.DataFrame, sample: pd.DataFrame) -> list[object]:
    """One row index per level of a text column that the sample lacks, so rare levels exist."""
    extra: list[object] = []
    for column in frame.columns:
        series = frame[column]
        if not _is_label(series):
            continue
        firsts = series.dropna().drop_duplicates()
        if len(firsts) > COVER_MAX_LEVELS:
            continue
        seen = set(sample[column].dropna().tolist())
        extra.extend(index for index, level in firsts.items() if level not in seen)
    return extra


def rare_values(frame: pd.DataFrame, sample: pd.DataFrame, seed: int) -> list[object]:
    """Row indices that give the rarer value of each two-valued column RARE_MIN rows in the sample.

    A clinic table (r_20261009T083216_35c688) had a major bleed in 2 % of 3000 patients; the
    200-row sample held none, every model of the outcome failed its smoke run, and the run failed
    although the full data has 58 bleeds.
    """
    rng = np.random.default_rng(seed)
    extra: list[object] = []
    for column in frame.columns:
        counts = frame[column].value_counts(dropna=True)
        if len(counts) != 2:
            continue
        rare = counts.index[-1]
        need = min(RARE_MIN, int(counts.iloc[-1])) - int((sample[column] == rare).sum())
        if need <= 0:
            continue
        pool = frame.index[(frame[column] == rare).to_numpy()].difference(sample.index)
        extra.extend(rng.choice(pool.to_numpy(), size=min(need, len(pool)), replace=False))
    return extra


def sample_frame(frame: pd.DataFrame, target: int, seed: int) -> pd.DataFrame:
    """About `target` rows; whole groups of the id column when one repeats, else random rows.

    Every level of a text column with few levels appears at least once, and the rarer value of a
    two-valued column at least RARE_MIN times when the data has that many.
    """
    column = group_column(frame)
    if column is None:
        sample = frame.sample(n=target, random_state=seed)
        index = sample.index.union(missing_levels(frame, sample))
        index = index.union(rare_values(frame, frame.loc[index], seed))
        return frame.loc[index].sort_index()
    sizes = frame[column].value_counts(dropna=True)
    order = sizes.index.to_numpy()[np.random.default_rng(seed).permutation(len(sizes))]
    counts = sizes.loc[order].to_numpy().cumsum()
    keep = set(order[: int(np.searchsorted(counts, target)) + 1].tolist())
    sample = frame[frame[column].isin(keep)]
    keep.update(frame.loc[missing_levels(frame, sample), column].dropna().tolist())
    sample = frame[frame[column].isin(keep)]
    keep.update(frame.loc[rare_values(frame, sample, seed), column].dropna().tolist())
    return frame[frame[column].isin(keep)].sort_index()
