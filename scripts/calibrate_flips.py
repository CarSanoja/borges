"""Offline calibration of the bounded flip search on synthetic checkout datasets.

Every run uses the scripted fixtures of cases/checkout_ab; the analysis numbers are computed
from each generated dataset, no model is called."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from borges.evaluation.calibration_grid import full_cells, smoke_cells
from borges.evaluation.calibration_study import result_document, run_study

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "evidence" / "calibration.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="two datasets, a few seconds")
    parser.add_argument("--scale", type=float, default=1.0, help="multiplier on replicates")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--rows", type=Path, default=None, help="incremental jsonl, resumable")
    args = parser.parse_args()
    cells = smoke_cells() if args.smoke else full_cells(args.scale)
    rows_path = args.rows or args.out.with_suffix(".rows.jsonl")
    rows, scanned = run_study(cells, rows_path, args.workers)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result_document(rows, scanned, cells), indent=1) + "\n")
    print(f"{len(rows)} runs -> {args.out}")


if __name__ == "__main__":
    main()
