"""Build data.parquet of the held-out Study 2 cases from Durante et al. (2013) on OSF.

Steegen et al. (2016) published the raw data at https://osf.io/zj68b/ with the original author's
permission to make them public; their supplement documents the cleaning already applied. The OSF
project states no licence, so the data are downloaded here and never committed.
"""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").is_file())
RAW_DIR = ROOT / "data" / "raw"
CASE_DIRS = (HERE.parent / "cases" / "fertility_vote", HERE.parent / "cases" / "fertility_social")
DATASET_URL = "https://osf.io/download/rvf9x/"
SHA256 = "85c0e63e5c7aaa9f0f03e669ee0480bc64fd68c56e9fa79f300df42ac42c94d5"
RAW_NAME = "durante_study2.txt"
DATE_COLUMNS = (
    "DateTesting",
    "StartDateofLastPeriod",
    "StartDateofPeriodBeforeLast",
    "StartDateNext",
)


def fetch_cached() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_DIR / RAW_NAME
    if not target.exists():
        with urllib.request.urlopen(DATASET_URL, timeout=120) as response:
            target.write_bytes(response.read())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"{target} has sha256 {digest}, expected {SHA256}")
    return target


def build_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, sep=r"\s+", na_values="NA")
    for column in DATE_COLUMNS:
        frame[column] = pd.to_datetime(frame[column], format="%m/%d/%y")
    return frame


def main() -> None:
    frame = build_frame(fetch_cached())
    for case_dir in CASE_DIRS:
        frame.to_parquet(case_dir / "data.parquet", index=False, compression="zstd")
        print(f"wrote {len(frame)} rows to {case_dir.relative_to(ROOT)}/data.parquet")


if __name__ == "__main__":
    main()
