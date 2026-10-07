from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from borges.analysis.models import AnalysisResult, CodingSummary
from borges.analysis.reference_writer import Fix
from borges.garden.models import SearchSummary, Universe
from borges.runs import baseline_confirm
from borges.runs.baseline_confirm import confirm_baseline
from borges.runs.baseline_reference import References
from borges.runs.judged_ledger import JudgedLedger
from tests.analysis.fakes import make_plan

PUBLISHED = AnalysisResult(estimate=-1.623, ci_low=-2.72, ci_high=-0.52, p_value=0.0038, n=303)
WRONG = AnalysisResult(estimate=-0.795, ci_low=-1.35, ci_high=-0.24, p_value=0.0047, n=301)
OTHER = AnalysisResult(estimate=-1.2, ci_low=-2.2, ci_high=-0.16, p_value=0.02, n=344)
FIXED = "def apply(df, ctx):\n    return df\n"


def universe(result: AnalysisResult | None) -> Universe:
    status = "done" if result is not None else "failed"
    return Universe(
        id="u_base", choices={}, changed=[], kind="baseline", status=status, result=result
    )


def pipeline(**fields: Any) -> SimpleNamespace:
    saved: list[str] = []
    defaults: dict[str, Any] = {
        "llm": None,
        "executor": object(),
        "restored": None,
        "search": SearchSummary(),
        "caveats": [],
        "smoke": None,
        "planned": None,
        "judged": JudgedLedger(),
        "coding": CodingSummary(),
        "saved": saved,
        "checkpoint": lambda key, payload: saved.append(key),
    }
    return SimpleNamespace(**{**defaults, **fields})


def analysis_plan():
    plan = make_plan(with_code=True)
    plan.analysis = "the published analysis"
    return plan


def script(monkeypatch, references, fixes=(), reruns=()):
    """references: the results of the implementations that ran, None for one that failed."""
    script.dropped = []
    fix_queue, rerun_queue = list(fixes), list(reruns)
    ran: list[dict[str, str]] = []

    async def found(llm, executor, plan):
        out = References()
        for i, result in enumerate(references):
            if result is None:
                out.errors.append(f"implementation {i + 1} failed")
            else:
                out.results.append((result, f"code {i + 1}"))
        return out

    async def propose(llm, plan, traces, ours, theirs, code, dropped=None):
        script.dropped.append(dropped)
        return fix_queue.pop(0) if fix_queue else []

    monkeypatch.setattr(baseline_confirm, "agreed_reference", found)
    monkeypatch.setattr(baseline_confirm, "propose_fixes", propose)

    async def rerun(choices):
        ran.append(dict(choices))
        return universe(rerun_queue.pop(0))

    rerun.calls = ran
    return rerun


async def test_two_implementations_that_match_the_baseline_confirm_it(monkeypatch) -> None:
    rerun = script(monkeypatch, [PUBLISHED, PUBLISHED])
    p = pipeline()
    out = await confirm_baseline(p, analysis_plan(), universe(PUBLISHED), rerun)
    assert out.result == PUBLISHED and p.search.reference == "agrees" and p.caveats == []


async def test_an_implementation_that_copies_the_baseline_does_not_outvote_two_others(
    monkeypatch,
) -> None:
    fix = Fix(step_id="d1", option_id="keep", problem="kept the two hand-set rows", code=FIXED)
    rerun = script(monkeypatch, [PUBLISHED, WRONG, PUBLISHED], fixes=[[fix]], reruns=[PUBLISHED])
    p = pipeline()
    out = await confirm_baseline(p, analysis_plan(), universe(WRONG), rerun)
    assert out.result == PUBLISHED and p.search.reference == "repaired"
    assert p.search.reference_results == [PUBLISHED, WRONG, PUBLISHED]


async def test_two_agreeing_implementations_repair_the_step_that_departs(monkeypatch) -> None:
    fix = Fix(step_id="d1", option_id="keep", problem="dropped two rows set by hand", code=FIXED)
    rerun = script(monkeypatch, [PUBLISHED, PUBLISHED], fixes=[[fix]], reruns=[PUBLISHED])
    p, plan = pipeline(), analysis_plan()
    out = await confirm_baseline(p, plan, universe(WRONG), rerun)
    assert out.result == PUBLISHED and p.search.reference == "repaired"
    assert plan.step("d1").option("keep").code == FIXED
    assert "first gave -0.7950" in p.caveats[0] and "dropped two rows set by hand" in p.caveats[0]
    assert p.saved == ["stage:coded"]


async def test_a_repair_that_does_not_close_the_gap_is_undone(monkeypatch) -> None:
    fix = Fix(step_id="d1", option_id="keep", problem="p", code=FIXED)
    rerun = script(monkeypatch, [PUBLISHED, PUBLISHED], fixes=[[fix], []], reruns=[OTHER, WRONG])
    p, plan = pipeline(), analysis_plan()
    before = plan.step("d1").option("keep").code
    out = await confirm_baseline(p, plan, universe(WRONG), rerun)
    assert plan.step("d1").option("keep").code == before
    assert out.result == WRONG and p.search.reference == "disagrees"
    assert "does not match your analysis" in p.caveats[0] and len(rerun.calls) == 2


async def test_implementations_that_never_agree_are_reported_as_unresolved(monkeypatch) -> None:
    rerun = script(monkeypatch, [PUBLISHED, OTHER, WRONG])
    p = pipeline()
    await confirm_baseline(p, analysis_plan(), universe(WRONG), rerun)
    assert p.search.reference == "unresolved" and "could not be confirmed" in p.caveats[0]
    assert "-1.6230" in p.caveats[0] and "n 344" in p.caveats[0]


async def test_one_implementation_alone_does_not_confirm_the_baseline(monkeypatch) -> None:
    rerun = script(monkeypatch, [PUBLISHED, None, None])
    p = pipeline()
    await confirm_baseline(p, analysis_plan(), universe(PUBLISHED), rerun)
    assert p.search.reference == "unresolved"


@pytest.mark.parametrize("analysis", ["", "the published analysis"])
async def test_no_analysis_or_a_failed_baseline_is_left_alone(monkeypatch, analysis) -> None:
    rerun = script(monkeypatch, [])
    plan = analysis_plan()
    plan.analysis = analysis
    p = pipeline()
    base = universe(PUBLISHED if not analysis else None)
    assert await confirm_baseline(p, plan, base, rerun) is base
    assert p.search.reference is None


async def test_an_implementation_that_cannot_run_is_reported(monkeypatch) -> None:
    rerun = script(monkeypatch, [None, None, None])
    p = pipeline()
    await confirm_baseline(p, analysis_plan(), universe(PUBLISHED), rerun)
    assert p.search.reference == "unchecked" and "implementation 1 failed" in p.caveats[0]


async def test_a_denied_repair_reports_the_mismatch_and_changes_nothing(monkeypatch) -> None:
    from borges.gateway.errors import GatewayDenied

    rerun = script(monkeypatch, [PUBLISHED, PUBLISHED], reruns=[WRONG])

    async def denied(*_args):
        raise GatewayDenied("max_tokens", "above the ceiling")

    monkeypatch.setattr(baseline_confirm, "propose_fixes", denied)
    p = pipeline()
    base = universe(WRONG)
    assert await confirm_baseline(p, analysis_plan(), base, rerun) is base
    assert p.search.reference == "disagrees" and "does not match" in p.caveats[0]
    assert rerun.calls == []


async def test_an_error_while_writing_leaves_the_run_as_it_was(monkeypatch) -> None:
    from borges.llm.client import LLMError

    rerun = script(monkeypatch, [])

    async def broken(*_args):
        raise LLMError("budget for this run is spent")

    monkeypatch.setattr(baseline_confirm, "agreed_reference", broken)
    p = pipeline()
    base = universe(PUBLISHED)
    assert await confirm_baseline(p, analysis_plan(), base, rerun) is base
    assert p.search.reference == "unchecked" and "budget" in p.caveats[0]


async def test_a_confirmed_starting_point_withdraws_the_planner_s_doubts(monkeypatch) -> None:
    rerun = script(monkeypatch, [PUBLISHED, PUBLISHED])
    doubt = (
        "The starting point may not be exactly your analysis, so read the original result with "
        "care: step7: the analysis says model SEs."
    )
    p = pipeline()
    p.caveats.extend([doubt, "Another caveat."])
    await confirm_baseline(p, analysis_plan(), universe(PUBLISHED), rerun)
    assert p.caveats[0] == "Another caveat."
    assert "listed 1 possible difference;" in p.caveats[1] and "it does not change" in p.caveats[1]


async def test_the_users_own_option_dropped_in_coding_is_restored_by_the_repair(
    monkeypatch,
) -> None:
    """fertility_vote on 7 October, run 18: the user's cycle day failed its smoke run, an
    alternative became the default, and the repair could only correct the options left."""
    from borges.analysis.coder_smoke import FAILED_NOTE
    from borges.analysis.smoke_types import Outcome
    from borges.runs.pipeline_caveats import default_departures

    planned = analysis_plan()
    plan = planned.model_copy(deep=True)
    step = plan.step("d1")
    step.options = [o for o in step.options if o.id != "keep"]
    step.options[0].is_default = True
    failed = Outcome(
        planned.step("d1").option("keep"), "failed", 3, "TypeError: str date", None, []
    )
    note = FAILED_NOTE.format(label="Label keep", title="Outliers", error="TypeError")
    p = pipeline(
        planned=planned,
        smoke=SimpleNamespace(state=SimpleNamespace(outcomes={"d1": [failed]}, notes=[])),
        caveats=[note, *default_departures(planned, plan)],
    )
    fix = Fix(step_id="d1", option_id="keep", problem="ctx name read as a date", code=FIXED)
    rerun = script(monkeypatch, [PUBLISHED, PUBLISHED], fixes=[[fix]], reruns=[PUBLISHED])
    result = await confirm_baseline(p, plan, universe(WRONG), rerun)
    assert result.result == PUBLISHED and p.search.reference == "repaired"
    assert [(o.id, o.is_default) for o in plan.step("d1").options] == [
        ("keep", True),
        ("trim", False),
    ]
    assert plan.step("d1").default.code == FIXED
    offered = script.dropped[0]["d1"]
    assert offered[0].id == "keep" and offered[1] == "TypeError: str date"
    assert not any("could not run" in c or "failed its smoke run" in c for c in p.caveats)
    assert any(c.startswith("The step-by-step code of your analysis first gave") for c in p.caveats)


async def test_a_restored_option_that_does_not_close_the_gap_is_taken_out_again(
    monkeypatch,
) -> None:
    from borges.analysis.smoke_types import Outcome
    from borges.runs.pipeline_caveats import default_departures

    planned = analysis_plan()
    plan = planned.model_copy(deep=True)
    step = plan.step("d1")
    step.options = [o for o in step.options if o.id != "keep"]
    step.options[0].is_default = True
    failed = Outcome(planned.step("d1").option("keep"), "failed", 3, "TypeError", None, [])
    departures = default_departures(planned, plan)
    p = pipeline(
        planned=planned,
        smoke=SimpleNamespace(state=SimpleNamespace(outcomes={"d1": [failed]}, notes=[])),
        caveats=list(departures),
    )
    fix = Fix(step_id="d1", option_id="keep", problem="p", code=FIXED)
    rerun = script(monkeypatch, [PUBLISHED, PUBLISHED], fixes=[[fix]], reruns=[OTHER, WRONG])
    await confirm_baseline(p, plan, universe(WRONG), rerun)
    assert p.search.reference == "disagrees"
    assert [o.id for o in plan.step("d1").options] == ["trim"]
    assert departures[0] in p.caveats
