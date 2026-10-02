from __future__ import annotations

import shutil
from pathlib import Path

from borges.config import REPO_ROOT

LIVE_FIXTURE = Path(__file__).parent / "fixtures" / "live_checkout_ab_events.jsonl"
LIVE_RUN_ID = "r_20261002T111156_5ae545"
LIVE_FLIP_UNIVERSE = "u_7563a47c79"


def make_cases_dir(
    root: Path, *, live: bool = True, scripted: bool = True, live_only: bool = False
) -> Path:
    source = REPO_ROOT / "cases" / "checkout_ab"
    target = root / "cases" / "checkout_ab"
    target.mkdir(parents=True)
    shutil.copyfile(source / "data.parquet", target / "data.parquet")
    spec = (source / "case.json").read_text(encoding="utf-8")
    if live_only:
        spec = spec.rstrip().rstrip("}").rstrip() + ',\n  "live_only": true\n}\n'
    (target / "case.json").write_text(spec, encoding="utf-8")
    if scripted:
        (target / "recorded").mkdir()
        shutil.copyfile(source / "recorded" / "events.jsonl", target / "recorded" / "events.jsonl")
    if live:
        (target / "recorded-live").mkdir()
        shutil.copyfile(LIVE_FIXTURE, target / "recorded-live" / "events.jsonl")
    return root / "cases"
