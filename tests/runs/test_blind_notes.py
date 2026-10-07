from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from borges.analysis.models import ColumnProfile, DatasetProfile
from borges.analysis.profile import blind_profile, profile_dataframe
from borges.cases.registry import CaseRegistry
from borges.config import Settings
from borges.runs import pipeline
from borges.runs.inputs import resolve_run
from borges.runs.models import RunRequest
from borges.runs.pipeline import BLIND_CAVEAT
from tests.runs.engine_fakes import Scenario, install
from tests.runs.fakes import make_plan, make_rig

NOTE = "True for internal staff, not genuine customers"


def noted_profile() -> DatasetProfile:
    return DatasetProfile(
        name="d",
        n_rows=3,
        columns=[
            ColumnProfile(name="is_internal", dtype="bool", n_missing=0, n_unique=2, note=NOTE),
            ColumnProfile(name="y", dtype="int64", n_missing=0, n_unique=2),
        ],
    )


def test_blind_profile_strips_every_note_and_keeps_the_data() -> None:
    blind = blind_profile(noted_profile())
    assert [c.note for c in blind.columns] == [None, None]
    assert [c.name for c in blind.columns] == ["is_internal", "y"]
    assert noted_profile().columns[0].note == NOTE


def test_resolve_run_carries_the_flag(tmp_path: Path) -> None:
    registry = CaseRegistry(Path(__file__).resolve().parents[2] / "cases")
    settings = Settings()
    plain = resolve_run(RunRequest(case_id="checkout_ab"), registry, settings)
    blind = resolve_run(RunRequest(case_id="checkout_ab", blind_notes=True), registry, settings)
    assert plain.blind_notes is False and blind.blind_notes is True
    assert blind.column_notes


def test_the_request_defaults_to_not_blind() -> None:
    assert RunRequest(case_id="x").blind_notes is False


@pytest.fixture
def scenario(monkeypatch: pytest.MonkeyPatch) -> Scenario:
    value = Scenario()
    install(monkeypatch, value)
    return value


@pytest.mark.parametrize("blind", [False, True])
async def test_the_planner_sees_notes_only_when_the_run_is_not_blind(
    tmp_path: Path, scenario: Scenario, monkeypatch: pytest.MonkeyPatch, blind: bool
) -> None:
    seen: list[DatasetProfile] = []

    def profile(df: Any, name: str, **_: Any) -> DatasetProfile:
        return noted_profile()

    async def plan(llm: Any, profile: DatasetProfile, question: str, rule: Any, *_: Any):
        seen.append(profile)
        return make_plan()

    monkeypatch.setattr(pipeline, "profile_dataframe", profile)
    monkeypatch.setattr(pipeline, "plan_analysis", plan)
    rig = make_rig(tmp_path)
    snapshot = await rig.orchestrator.execute(
        "r_test", RunRequest(case_id="demo", blind_notes=blind)
    )
    notes = [c.note for c in seen[0].columns]
    assert notes == ([None, None] if blind else [NOTE, None])
    assert snapshot.report is not None
    assert (BLIND_CAVEAT in snapshot.report.caveats) is blind


def test_profile_dataframe_notes_are_what_blind_mode_removes() -> None:
    import pandas as pd

    frame = pd.DataFrame({"a": [1, 2]})
    noted = profile_dataframe(frame, "d", column_notes={"a": "meaning"})
    assert noted.columns[0].note == "meaning"
    assert blind_profile(noted).columns[0].note is None
