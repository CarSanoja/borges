from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

import pandas as pd

from borges.analysis import profile as profile_module
from borges.analysis.column_names import safe_identifier
from borges.analysis.models import DatasetProfile
from borges.api.table_reader import read_table
from borges.armor.profile_guard import guard_profile
from borges.armor.upload_scan import PiiSummary, scan_dataframe

MAX_BYTES = 20 * 1024 * 1024
MIN_COLUMNS = 2
MIN_ROWS = 20
_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def drop_empty_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    empty = [c for c in df.columns if df[c].isna().all()]
    dropped = [{"column": str(c), "reason": "every value is empty"} for c in empty]
    return df.drop(columns=empty), dropped


def normalise_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    seen: set[str] = set()
    names: list[str] = []
    mapping: dict[str, str] = {}
    for original in df.columns:
        base = safe_identifier(original)
        candidate = base
        counter = 2
        while candidate in seen:
            candidate = f"{base}_{counter}"
            counter += 1
        seen.add(candidate)
        names.append(candidate)
        mapping[candidate] = str(original)
    return df.set_axis(names, axis=1), mapping


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
        df = read_table(csv_bytes, filename)
        df, dropped = drop_empty_columns(df)
        if df.shape[1] < MIN_COLUMNS:
            raise ValueError(
                f"The table needs at least {MIN_COLUMNS} columns with data; "
                f"it has {df.shape[1]} after {len(dropped)} empty columns were dropped."
            )
        if df.shape[0] < MIN_ROWS:
            raise ValueError(
                f"The table has {df.shape[0]} rows and needs at least {MIN_ROWS}: "
                "with fewer rows a model with an exposure and a few covariates has too few "
                "degrees of freedom left to estimate its uncertainty."
            )
        df, columns = normalise_columns(df)
        name = Path(filename).name or "upload.csv"
        profile, _ = guard_profile(profile_module.profile_dataframe(df, name))
        pii = scan_dataframe(df)
        upload_id = uuid.uuid4().hex
        self.directory.mkdir(parents=True, exist_ok=True)
        parquet = self._parquet_path(upload_id)
        df.to_parquet(parquet, index=False)
        if self.quota_bytes is not None and self._used_bytes() > self.quota_bytes:
            parquet.unlink(missing_ok=True)
            raise UploadQuotaError("The upload storage of this demo is full.")
        meta = {
            "name": name,
            "columns": columns,
            "pii": pii.model_dump(mode="json"),
            "dropped_columns": dropped,
        }
        self._meta_path(upload_id).write_text(json.dumps(meta))
        return upload_id, profile

    def pii(self, upload_id: str) -> PiiSummary:
        if not _ID_PATTERN.match(upload_id) or not self._meta_path(upload_id).exists():
            raise KeyError(upload_id)
        stored = json.loads(self._meta_path(upload_id).read_text()).get("pii")
        return PiiSummary.model_validate(stored) if stored else PiiSummary()

    def dropped_columns(self, upload_id: str) -> list[dict[str, str]]:
        if not _ID_PATTERN.match(upload_id) or not self._meta_path(upload_id).exists():
            raise KeyError(upload_id)
        return json.loads(self._meta_path(upload_id).read_text()).get("dropped_columns", [])

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
