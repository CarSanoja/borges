from __future__ import annotations

import urllib.request
from pathlib import Path

import pandas as pd

CASE_DIR = Path(__file__).resolve().parent
RAW_DIR = CASE_DIR.parents[1] / "data" / "raw"
BLADE_COMMIT = "9417ac59ae46fbb8a71635c77934e1a5c334f683"
DATASET_URL = (
    "https://raw.githubusercontent.com/behavioral-data/BLADE/"
    f"{BLADE_COMMIT}/blade_bench/datasets/teachingratings/data.csv"
)
CSV_NAME = "blade_teachingratings.csv"


def fetch_cached() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_DIR / CSV_NAME
    if not target.exists():
        with urllib.request.urlopen(DATASET_URL, timeout=120) as response:
            target.write_bytes(response.read())
    return target


def build_frame(csv_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    return frame.drop(columns=[c for c in frame.columns if c in ("rownames", "Unnamed: 0")])


def main() -> None:
    frame = build_frame(fetch_cached())
    frame.to_parquet(CASE_DIR / "data.parquet", index=False, compression="zstd")
    print(f"wrote {len(frame)} rows")


if __name__ == "__main__":
    main()
