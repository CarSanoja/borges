from __future__ import annotations

import urllib.request
from pathlib import Path

import pandas as pd

CASE_DIR = Path(__file__).resolve().parent
RAW_DIR = CASE_DIR.parents[1] / "data" / "raw"
BLADE_COMMIT = "fc2e0fd187ba2751937387b26015ef002ee03b53"
DATASET_URL = (
    "https://raw.githubusercontent.com/behavioral-data/BLADE/"
    f"{BLADE_COMMIT}/blade_bench/datasets/fertility/data.csv"
)
CSV_NAME = "blade_fertility.csv"
DATE_COLUMNS = ("DateTesting", "StartDateofLastPeriod", "StartDateofPeriodBeforeLast")


def fetch_cached() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_DIR / CSV_NAME
    if not target.exists():
        with urllib.request.urlopen(DATASET_URL, timeout=120) as response:
            target.write_bytes(response.read())
    return target


def build_frame(csv_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    for column in DATE_COLUMNS:
        frame[column] = pd.to_datetime(frame[column], format="%m/%d/%y")
    return frame


def main() -> None:
    frame = build_frame(fetch_cached())
    frame.to_parquet(CASE_DIR / "data.parquet", index=False, compression="zstd")
    print(f"wrote {len(frame)} rows")


if __name__ == "__main__":
    main()
