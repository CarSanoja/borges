from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from borges.cases.recording_stamp import read_meta, stamp_from_meta, write_stamp

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ("recorded-live", "recorded")


def first_run_id(events: Path) -> str | None:
    try:
        with events.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    raw = json.loads(line)
                    return raw.get("run_id") if isinstance(raw, dict) else None
    except (OSError, ValueError):
        return None
    return None


def parse_commits(items: list[str]) -> tuple[str | None, dict[str, str]]:
    default: str | None = None
    per_case: dict[str, str] = {}
    for item in items:
        case, sep, commit = item.partition("=")
        if sep:
            per_case[case] = commit
        else:
            default = item
    return default, per_case


def stamp_folder(folder: Path, case_id: str, runs: Path, commit: str | None) -> Path | None:
    run_id = first_run_id(folder / "events.jsonl")
    if run_id is None:
        return None
    meta = read_meta(runs / run_id)
    return write_stamp(folder, stamp_from_meta(meta, run_id, case_id, commit, None))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Write recording.json for existing recordings")
    parser.add_argument("--commit", action="append", default=[], help="HASH or CASE=HASH")
    parser.add_argument("--cases-dir", type=Path, default=ROOT / "cases")
    parser.add_argument("--runs-dir", type=Path, default=ROOT / "runs")
    parser.add_argument("--folder", action="append", choices=FOLDERS)
    args = parser.parse_args(argv)
    default, per_case = parse_commits(args.commit)
    folders = args.folder or ["recorded-live"]
    stamped = 0
    for case_dir in sorted(p for p in args.cases_dir.iterdir() if (p / "case.json").is_file()):
        for name in folders:
            folder = case_dir / name
            commit = per_case.get(case_dir.name, default)
            target = stamp_folder(folder, case_dir.name, args.runs_dir, commit)
            if target is not None:
                stamped += 1
                print(f"{target} commit={commit}")
    print(f"stamped {stamped}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
