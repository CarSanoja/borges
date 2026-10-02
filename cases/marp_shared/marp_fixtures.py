from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marp_judgements import VERDICTS
from marp_options import option_codes
from marp_plan import validated_planner

from borges.analysis.schemas import AdversaryOutput, CoderOutput, NarratorOutput
from borges.cases.judge_fixtures import planner_judge_outputs

FIXTURE_MODEL = "scripted-fixture"
NO_USAGE = {"tokens_in": 0, "tokens_out": 0}


def fixture_file(fixtures_dir: Path, key: str) -> Path:
    return fixtures_dir / f"{key.replace(':', '__')}.json"


def write_fixture(fixtures_dir: Path, key: str, parsed: Any) -> None:
    payload = {"model": FIXTURE_MODEL, "text": json.dumps(parsed), "parsed": parsed, **NO_USAGE}
    path = fixture_file(fixtures_dir, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def write_static_fixtures(fixtures_dir: Path, rq: int) -> None:
    for stale in fixtures_dir.glob("coder__*.json"):
        stale.unlink()
    planner = validated_planner(rq)
    write_fixture(fixtures_dir, "planner", planner.model_dump())
    for stale in fixtures_dir.glob("judge__planner__*.json"):
        stale.unlink()
    for key, output in planner_judge_outputs(planner, VERDICTS).items():
        write_fixture(fixtures_dir, f"judge:planner:{key}", output.model_dump())
    for key, code in option_codes(rq).items():
        write_fixture(fixtures_dir, f"coder:{key}", CoderOutput(code=code).model_dump())
    write_fixture(fixtures_dir, "adversary", AdversaryOutput(proposals=[]).model_dump())


def write_narrator(fixtures_dir: Path, narrator: NarratorOutput) -> None:
    write_fixture(fixtures_dir, "narrator", narrator.model_dump())
