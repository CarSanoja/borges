from __future__ import annotations

import pandas as pd

from borges.analysis.models import DatasetProfile


def profile_dataframe(df: pd.DataFrame, name: str, sample: int = 5) -> DatasetProfile:
    raise NotImplementedError
