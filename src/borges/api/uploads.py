from __future__ import annotations

import io
import json
import re
import uuid
from pathlib import Path

import pandas as pd

from borges.analysis import profile as profile_module
from borges.analysis.models import DatasetProfile

MAX_BYTES = 20 * 1024 * 1024
MIN_COLUMNS = 2
MIN_ROWS = 50
_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class UploadQuotaError(ValueError):
    pass


class UploadStore:
    def __init__(self, directory: Path, quota_mb: int | None = None) -> None:
        self.directory = Path(directory)
        self.quota_bytes = None if quota_mb is None else quota_mb * 1024 * 1024

    def _used_bytes(self) -> int:
        if not self.directory.is_dir():
            return 0
        return sum(p.stat().st_size for p in self.directory.iterdir() if p.is_file())

    def put(self, csv_bytes: bytes, filename: str) -> tuple[str, DatasetProfile]:
        if len(csv_bytes) > MAX_BYTES:
            raise ValueError("The file is larger than 20 MB.")
        if not csv_bytes.strip():
            raise ValueError("The file is empty.")
        try:
            df = pd.read_csv(io.BytesIO(csv_bytes))
        except Exception as exc:
            raise ValueError(f"The file is not a readable CSV: {exc}") from exc
        if df.shape[1] < MIN_COLUMNS:
            raise ValueError(f"The CSV needs at least {MIN_COLUMNS} columns.")
        if df.shape[0] < MIN_ROWS:
            raise ValueError(f"The CSV needs at least {MIN_ROWS} rows.")
        name = Path(filename).name or "upload.csv"
        profile = profile_module.profile_dataframe(df, name)
        upload_id = uuid.uuid4().hex
        self.directory.mkdir(parents=True, exist_ok=True)
        parquet = self._parquet_path(upload_id)
        df.to_parquet(parquet, index=False)
        if self.quota_bytes is not None and self._used_bytes() > self.quota_bytes:
            parquet.unlink(missing_ok=True)
            raise UploadQuotaError("The upload storage of this demo is full.")
        self._meta_path(upload_id).write_text(json.dumps({"name": name}))
        return upload_id, profile

    def get(self, upload_id: str) -> tuple[bytes, str]:
        if not _ID_PATTERN.match(upload_id):
            raise KeyError(upload_id)
        parquet = self._parquet_path(upload_id)
        meta = self._meta_path(upload_id)
        if not parquet.exists() or not meta.exists():
            raise KeyError(upload_id)
        name = json.loads(meta.read_text())["name"]
        return parquet.read_bytes(), name

    def _parquet_path(self, upload_id: str) -> Path:
        return self.directory / f"{upload_id}.parquet"

    def _meta_path(self, upload_id: str) -> Path:
        return self.directory / f"{upload_id}.json"
