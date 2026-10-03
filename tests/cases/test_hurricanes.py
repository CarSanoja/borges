from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

from borges.analysis import code_guard
from borges.analysis.schemas import (
    AdversaryOutput,
    CoderOutput,
    JudgeOutput,
    NarratorOutput,
    PlannerOutput,
)
from borges.bench.scripted_fixtures import replay_scripted
from borges.cases.models import CaseSpec
from borges.cases.registry import CaseRegistry
from borges.runs.state import fold

CASES_DIR = Path(__file__).resolve().parents[2] / "cases"
CASE_DIR = CASES_DIR / "hurricanes"
sys.path.insert(0, str(CASE_DIR))

from hurricanes_validation import DEFAULTS, STEP_ORDER, load_codes, run_universe  # noqa: E402

HINT_WORDS = re.compile(
    r"outlier|extreme|fragil|robust|katrina|audrey|leverage|critic|spurious|artefact|artifact",
    re.IGNORECASE,
)
SINGLE_FLIPS = {
    ("storms", "keep_all"),
    ("storms", "drop_top1"),
    ("damages", "linear_2013"),
}


@pytest.fixture(scope="module")
def case() -> CaseSpec:
    return CaseSpec.model_validate_json((CASE_DIR / "case.json").read_text())


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    return pd.read_parquet(CASE_DIR / "data.parquet")


@pytest.fixture(scope="module")
def codes() -> dict[str, str]:
    return load_codes()


@pytest.fixture(scope="module")
def snapshot():
    return replay_scripted(CASES_DIR, "hurricanes")


def test_case_card_is_complete(case: CaseSpec, frame: pd.DataFrame) -> None:
    assert case.question == "Do hurricanes with more feminine names cause more deaths?"
    assert case.decision_rule.comparator.value == "gt"
    assert case.decision_rule.threshold == 0.0
    assert case.decision_rule.alpha == 0.05
    assert len(frame) == 94
    card = CaseRegistry(CASES_DIR).card("hurricanes")
    assert card.n_rows == 94 and card.has_recording


def test_column_notes_are_neutral_and_cover_real_columns(
    case: CaseSpec, frame: pd.DataFrame
) -> None:
    assert set(case.column_notes) <= set(frame.columns)
    for note in case.column_notes.values():
        assert HINT_WORDS.search(note) is None


def test_reference_lane_quotes_the_specification_curve(case: CaseSpec) -> None:
    assert "1,728" in (case.reference_label or "")
    medians = [r for r in case.reference if "median" in r.label.lower()]
    assert medians and medians[0].estimate == pytest.approx(1.56)
    readme = (CASE_DIR / "README.md").read_text()
    for needle in ("37 of 1,728", "Table 2, p. 6", "p. 4", "ODC-By", "Jung", "scripted"):
        assert needle in readme


def test_fixtures_match_their_schemas() -> None:
    fixtures = CASE_DIR / "fixtures"
    schemas = {"planner": PlannerOutput, "adversary": AdversaryOutput, "narrator": NarratorOutput}
    for name, schema in schemas.items():
        schema.model_validate(json.loads((fixtures / f"{name}.json").read_text())["parsed"])
    for path in fixtures.glob("judge__*.json"):
        JudgeOutput.model_validate(json.loads(path.read_text())["parsed"])
    for path in fixtures.glob("coder__*.json"):
        CoderOutput.model_validate(json.loads(path.read_text())["parsed"])


def test_every_option_code_passes_the_guard(codes: dict[str, str]) -> None:
    for key, code in codes.items():
        step = key.split(".", 1)[0]
        kind = "model" if step == "model" else ("filter" if step == "storms" else "feature")
        assert code_guard.check_code(code, kind) == [], key


def test_baseline_replicates_without_significance(frame: pd.DataFrame, codes) -> None:
    raw = run_universe(frame, dict(DEFAULTS), codes)
    assert raw["n"] == 92
    assert raw["estimate"] == pytest.approx(4.114, abs=0.01)
    assert raw["p_value"] == pytest.approx(0.257, abs=0.005)


@pytest.mark.parametrize("step", [s for s in STEP_ORDER if s != "strength"])
def test_each_single_change_gives_the_documented_verdict(frame, codes, step) -> None:
    for key in codes:
        name, option_id = key.split(".", 1)
        if name != step or option_id == DEFAULTS[step] or option_id.startswith("adv_"):
            continue
        raw = run_universe(frame, {**DEFAULTS, step: option_id}, codes)
        significant = raw["estimate"] > 0 and raw["p_value"] < 0.05
        assert significant == ((step, option_id) in SINGLE_FLIPS), key


def test_scripted_run_flips_in_three_single_changes(snapshot) -> None:
    assert snapshot.status == "completed"
    report = snapshot.report
    assert report.original_verdict == "NO CLEAR EVIDENCE"
    assert report.minimal_flip is not None and len(report.minimal_flip.changes) == 1
    assert report.minimal_flip.flipped_verdict == "FEMININE NAMES DEADLIER"
    assert report.minimal_flip.reproduced is True
    singles = [u for u in snapshot.garden.universes.values() if u.kind == "single"]
    assert len(singles) == 14 and sum(bool(u.flipped) for u in singles) == 3


def test_recording_is_the_scripted_run(snapshot) -> None:
    events = CaseRegistry(CASES_DIR).recording("hurricanes")
    assert events
    recorded = fold(events)
    assert recorded.report.original_result == snapshot.report.original_result
    assert recorded.report.minimal_flip.universe_id == snapshot.report.minimal_flip.universe_id


def test_grid_summary_stays_near_the_published_curve() -> None:
    summary = json.loads((CASE_DIR / "grid_summary.json").read_text())
    assert summary["specifications"] == 1944
    assert summary["significant_predicted_direction"] == 59
    assert 0.01 < summary["share_significant"] < 0.06
    assert summary["median_estimate"] == pytest.approx(1.25, abs=0.01)
