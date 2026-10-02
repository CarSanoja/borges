from __future__ import annotations

import io

import pandas as pd

from borges.gateway.dataset_columns import columns_of


def test_reads_column_names_from_parquet_bytes() -> None:
    buffer = io.BytesIO()
    pd.DataFrame({"a": [1], "b": ["x"]}).to_parquet(buffer)
    assert columns_of(buffer.getvalue()) == {"a", "b"}


def test_unreadable_bytes_give_no_columns() -> None:
    assert columns_of(b"not parquet") == frozenset()
