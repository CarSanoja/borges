from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from borges.analysis.schemas import CoderOutput, JudgeOutput, NarratorOutput, PlannerOutput
from borges.cases.judge_fixtures import planner_judge_outputs
from borges.config import Settings
from borges.llm.scripted_provider import SCRIPTED_MODEL, fixture_name
from borges.runs.models import RunRequest, RunSnapshot


def write_fixture(directory: Path, key: str, parsed: Any) -> None:
    payload = {
        "model": SCRIPTED_MODEL,
        "text": json.dumps(parsed),
        "parsed": parsed,
        "tokens_in": 0,
        "tokens_out": 0,
    }
    directory.mkdir(parents=True, exist_ok=True)
    (directory / fixture_name(key)).write_text(json.dumps(payload, indent=2) + "\n")


def write_plan_fixtures(
    directory: Path,
    planner: PlannerOutput,
    codes: dict[str, str],
    verdicts: dict[str, tuple[float, str]],
    adversary: dict[str, Any],
    adversary_judges: dict[str, JudgeOutput],
    narrator: NarratorOutput,
) -> None:
    write_fixture(directory, "planner", planner.model_dump())
    for key, output in planner_judge_outputs(planner, verdicts).items():
        write_fixture(directory, f"judge:planner:{key}", output.model_dump())
    for key, code in codes.items():
        write_fixture(directory, f"coder:{key}", CoderOutput(code=code).model_dump())
    write_fixture(directory, "adversary", adversary)
    for key, output in adversary_judges.items():
        write_fixture(directory, f"judge:{key}", output.model_dump())
    write_fixture(directory, "narrator", narrator.model_dump())


def copy_fixtures(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for path in source.glob("*.json"):
        shutil.copyfile(path, target / path.name)


async def _replay(settings: Settings, case_id: str, max_universes: int | None) -> RunSnapshot:
    from borges.cli_runtime import execute_run

    request = RunRequest(case_id=case_id, llm="scripted", max_universes=max_universes)
    return await execute_run(settings, f"r_replay_{case_id}", request, False)


def replay_scripted(cases_dir: Path, case_id: str, max_universes: int | None = None) -> RunSnapshot:
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        settings = Settings(
            _env_file=None,
            borges_home=root / "home",
            borges_runs_dir=root / "runs",
            borges_cases_dir=cases_dir,
            otel_exporter_otlp_endpoint=None,
        )
        return asyncio.run(_replay(settings, case_id, max_universes))
