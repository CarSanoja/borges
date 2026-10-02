from __future__ import annotations

import io

import pandas as pd


def load_dataframe(data: bytes) -> pd.DataFrame:
    try:
        return pd.read_parquet(io.BytesIO(data))
    except Exception as exc:
        raise ValueError(f"the dataset is not a readable parquet file: {exc}") from exc
