from __future__ import annotations

import io

import pyarrow.parquet as pq


def columns_of(data: bytes) -> frozenset[str]:
    try:
        return frozenset(str(name) for name in pq.ParquetFile(io.BytesIO(data)).schema_arrow.names)
    except Exception:
        return frozenset()
