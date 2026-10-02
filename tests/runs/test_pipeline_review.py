from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from borges.analysis.models import AnalysisResult, CodingSummary
from borges.cli_render import coding_line
from borges.garden.models import Flip
from borges.llm.client import DEFAULT_ROLE_MODELS, SUPER, Role
from borges.runs import pipeline
from borges.runs.models import RunRequest
from borges.runs.pipeline_caveats import mirror_caveat
from tests.runs.engine_fakes import install
from tests.runs.engine_scenario import Scenario
from tests.runs.fakes import make_rig


def result(estimate: float, n: int = 100) -> AnalysisResult:
    return AnalysisResult(estimate=estimate, ci_low=-1, ci_high=1, p_value=0.01, n=n)


def flip(before: float, after: float, kind: str | None = "direction", n: int = 100) -> Flip:
    return Flip(
        universe_id="u",
        changes=[],
        baseline_result=result(before),
        flipped_result=result(after, n),
        baseline_verdict="SHIP",
        flipped_verdict="DON'T SHIP",
        kind=kind,
    )


def test_mirror_caveat_names_both_estimates() -> None:
    text = mirror_caveat(flip(0.0372, -0.0374), 0.0)
    assert text == (
        "the flipped estimate mirrors the original (+0.0372 vs -0.0374, same rows): check that "
        "the changed option did not reverse a variable's direction"
    )


@pytest.mark.parametrize(
    ("candidate", "threshold"),
    [
        (flip(0.0372, -0.0374, "significance"), 0.0),
        (flip(0.0372, -0.0374, n=90), 0.0),
        (flip(0.0372, -0.0200), 0.0),
        (flip(0.0372, 0.0100), 0.0),
        (flip(0.0372, -0.0374), 0.02),
        (None, 0.0),
    ],
)
def test_mirror_caveat_stays_quiet(candidate: Flip | None, threshold: float) -> None:
    assert mirror_caveat(candidate, threshold) is None


def test_mirror_caveat_is_measured_around_the_threshold() -> None:
    assert mirror_caveat(flip(0.30, 0.10), 0.2) is not None


def test_coding_line_reports_the_review() -> None:
    plain = coding_line(CodingSummary(options=9, smoke_tested=8))
    assert "reviewed" not in plain
    line = coding_line(
        CodingSummary(
            options=9,
            smoke_tested=8,
            steps_reviewed=4,
            options_flagged=2,
            options_dropped_by_review=1,
        )
    )
    assert line.endswith("4 steps reviewed, 2 options flagged, 1 dropped")


def test_reviewer_role_uses_the_super_model() -> None:
    assert DEFAULT_ROLE_MODELS[Role.REVIEWER] is SUPER


async def test_review_callback_emits_option_reviewed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, Scenario())

    async def code_plan(llm: Any, plan: Any, on_coded: Any, concurrency: int, **kwargs: Any):
        smoke = kwargs["smoke"]
        assert smoke.reviewer is not None
        await smoke.on_review("s1", "a", False, True, "swaps the groups", "m-super")
        return plan

    monkeypatch.setattr(pipeline, "code_plan", code_plan)
    rig = make_rig(tmp_path)
    await rig.orchestrator.execute("r_test", RunRequest(case_id="demo"))
    reviewed = [e.data for e in rig.store.events("r_test") if e.type == "option.reviewed"]
    assert reviewed == [
        {
            "step_id": "s1",
            "option_id": "a",
            "faithful": False,
            "changes_estimand": True,
            "problem": "swaps the groups",
            "model": "m-super",
        }
    ]
