from __future__ import annotations

import re

import numpy as np
import pandas as pd

ID_NAME = re.compile(r"(?:^|_)id$", re.IGNORECASE)
MIN_GROUPS = 20


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


def sample_frame(frame: pd.DataFrame, target: int, seed: int) -> pd.DataFrame:
    """About `target` rows; whole groups of the id column when one repeats, else random rows."""
    column = group_column(frame)
    if column is None:
        return frame.sample(n=target, random_state=seed).sort_index()
    sizes = frame[column].value_counts(dropna=True)
    order = sizes.index.to_numpy()[np.random.default_rng(seed).permutation(len(sizes))]
    counts = sizes.loc[order].to_numpy().cumsum()
    keep = order[: int(np.searchsorted(counts, target)) + 1]
    return frame[frame[column].isin(keep)].sort_index()
