from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

CASE_DIR = Path(__file__).resolve().parent
SOURCE_SUBPATH = Path("blade_bench") / "datasets" / "hurricane" / "data.csv"


def build(blade_dir: Path) -> Path:
    frame = pd.read_csv(blade_dir / SOURCE_SUBPATH)
    for name in ("name", "source"):
        frame[name] = frame[name].astype("string")
    target = CASE_DIR / "data.parquet"
    frame.to_parquet(target, index=False, compression="zstd")
    return target


def main() -> None:
    root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BORGES_BLADE_DIR", "")
    if not root:
        raise SystemExit("usage: prepare.py <path to a clone of github.com/behavioral-data/BLADE>")
    target = build(Path(root))
    print(f"wrote {target} rows={len(pd.read_parquet(target))}")


if __name__ == "__main__":
    main()
