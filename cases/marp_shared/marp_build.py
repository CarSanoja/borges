from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
from marp_fixtures import write_narrator, write_static_fixtures
from marp_grid import enumerate_grid, write_grid
from marp_narrate import narrate, story
from marp_reference import reference, team_summary

from borges.analysis.models import DecisionRule
from borges.analysis.schemas import NarratorOutput
from borges.cases.models import CaseSpec
from borges.runs.models import RunSnapshot

REFERENCE_CITATION = "Hoogeveen, Sarafoglou et al., 2022"
CASES = {
    1: {
        "id": "marp_religiosity",
        "title": "Religion and well-being",
        "question": "Do religious people self-report greater well-being?",
        "dataset_name": "marp_religiosity_wellbeing",
        "rule": DecisionRule(
            metric="standardised coefficient of religiosity on well-being",
            threshold=0.0,
            alpha=0.05,
            positive_label="POSITIVE ASSOCIATION",
            negative_label="NO CLEAR EVIDENCE",
        ),
    },
    2: {
        "id": "marp_norms",
        "title": "Religion, well-being and cultural norms",
        "question": (
            "Does the relation between religiosity and well-being depend on perceived "
            "cultural norms of religion?"
        ),
        "dataset_name": "marp_religiosity_wellbeing",
        "rule": DecisionRule(
            metric="standardised religiosity x cultural-norms interaction on well-being",
            threshold=0.0,
            alpha=0.05,
            positive_label="DEPENDS ON NORMS",
            negative_label="NO CLEAR EVIDENCE",
        ),
    },
}
CASES_DIR = Path(__file__).resolve().parents[1]
SCRATCH = Path(os.environ.get("MARP_SCRATCH", "/tmp/marp_build"))


def case_dir(rq: int) -> Path:
    return CASES_DIR / CASES[rq]["id"]


def write_spec(rq: int, subtitle: str, story_text: str) -> None:
    info = CASES[rq]
    teams = team_summary(rq)
    spec = CaseSpec(
        id=info["id"],
        title=info["title"],
        subtitle=subtitle,
        question=info["question"],
        decision_rule=info["rule"],
        dataset_name=info["dataset_name"],
        max_universes=40,
        reference_label=(
            f"{int(teams['n_teams'])} of 120 research teams that reported a standardised "
            f"effect ({REFERENCE_CITATION})"
        ),
        reference=reference(rq),
        story=story_text,
    )
    (case_dir(rq) / "case.json").write_text(spec.model_dump_json(indent=2) + "\n")


def subtitle_for(rq: int) -> str:
    teams = team_summary(rq)
    n, k = int(teams["n_teams"]), int(teams["n_significant"])
    if k == n:
        return f"{n} research teams. Same data. All {n} found a positive effect."
    return f"{n} research teams. Same data. {k} found an effect, {n - k} did not."


def run_scripted(rq: int) -> RunSnapshot:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "BORGES_RUNS_DIR": str(SCRATCH)}
    cmd = [
        "uv",
        "run",
        "--no-sync",
        "borges",
        "run",
        "--case",
        CASES[rq]["id"],
        "--llm",
        "scripted",
        "--json",
    ]
    done = subprocess.run(
        cmd, env=env, capture_output=True, text=True, check=True, cwd=CASES_DIR.parent
    )
    return RunSnapshot.model_validate_json(done.stdout)


def build(rq: int) -> None:
    directory = case_dir(rq)
    fixtures = directory / "fixtures"
    placeholder = NarratorOutput(narrative="placeholder", caveats=[])
    write_static_fixtures(fixtures, rq)
    write_narrator(fixtures, placeholder)
    write_spec(rq, subtitle_for(rq), "")
    snapshot = run_scripted(rq)
    teams = team_summary(rq)
    write_narrator(fixtures, narrate(snapshot, rq, teams))
    write_spec(rq, subtitle_for(rq), story(snapshot, rq, teams))
    if "--grid" in sys.argv:
        frame = pd.read_parquet(directory / "data.parquet")
        write_grid(directory, enumerate_grid(frame, rq, CASES[rq]["rule"]))
    print(json.dumps(snapshot.report.model_dump(mode="json")["n_universes"]))
