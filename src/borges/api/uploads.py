from __future__ import annotations

import io
import json
import re
import uuid
from pathlib import Path

import pandas as pd

from borges.analysis import profile as profile_module
from borges.analysis.code_guard_rules import FORBIDDEN_MODULES, FORBIDDEN_NAMES
from borges.analysis.models import DatasetProfile

MAX_BYTES = 20 * 1024 * 1024
PARQUET_MAGIC = b"PAR1"
MIN_COLUMNS = 2
MIN_ROWS = 50
_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def _is_parquet(content: bytes, filename: str) -> bool:
    return content[:4] == PARQUET_MAGIC or filename.lower().endswith(".parquet")


def _read_table(content: bytes, filename: str) -> pd.DataFrame:
    parquet = _is_parquet(content, filename)
    try:
        if parquet:
            return pd.read_parquet(io.BytesIO(content))
        return pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        kind = "parquet file" if parquet else "CSV"
        raise ValueError(f"The file is not a readable {kind}: {exc}") from exc


def _safe_identifier(raw: object) -> str:
    text = re.sub(r"[^a-z0-9_]", "_", str(raw).lower())
    text = re.sub(r"_{2,}", "_", text)
    if not text.strip("_"):
        return "column"
    if text[0].isdigit():
        text = f"_{text}"
    if text in FORBIDDEN_NAMES or text in FORBIDDEN_MODULES:
        text = f"{text}_col"
    return text


def normalise_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    seen: set[str] = set()
    names: list[str] = []
    mapping: dict[str, str] = {}
    for original in df.columns:
        base = _safe_identifier(original)
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
        df = _read_table(csv_bytes, filename)
        if df.shape[1] < MIN_COLUMNS:
            raise ValueError(f"The table needs at least {MIN_COLUMNS} columns.")
        if df.shape[0] < MIN_ROWS:
            raise ValueError(f"The table needs at least {MIN_ROWS} rows.")
        df, columns = normalise_columns(df)
        name = Path(filename).name or "upload.csv"
        profile = profile_module.profile_dataframe(df, name)
        upload_id = uuid.uuid4().hex
        self.directory.mkdir(parents=True, exist_ok=True)
        parquet = self._parquet_path(upload_id)
        df.to_parquet(parquet, index=False)
        if self.quota_bytes is not None and self._used_bytes() > self.quota_bytes:
            parquet.unlink(missing_ok=True)
            raise UploadQuotaError("The upload storage of this demo is full.")
        self._meta_path(upload_id).write_text(json.dumps({"name": name, "columns": columns}))
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
