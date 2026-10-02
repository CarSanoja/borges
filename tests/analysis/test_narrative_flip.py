from __future__ import annotations

from borges.analysis.models import AnalysisPlan, AnalysisResult, Option, Step
from borges.analysis.narrative_flip import (
    flip_sentence,
    has_sentence,
    insert_sentence,
    problems,
    wrong_labels,
)
from borges.garden.models import Change, Flip, Report
from tests.analysis.fakes import make_option, make_plan


def _option(option_id: str, label: str, default: bool = False) -> Option:
    return make_option(option_id, default).model_copy(update={"label": label})


def checkout_plan() -> AnalysisPlan:
    plan = make_plan()
    step = Step(
        id="step_filter_records",
        title="Filter records",
        kind="filter",
        description="d",
        options=[
            _option("opt_keep_all", "Keep all sessions", True),
            _option("opt_exclude_internal", "Exclude internal sessions"),
            _option("opt_exclude_both", "Exclude internal and bot-like sessions"),
        ],
    )
    return plan.model_copy(update={"steps": [step, *plan.steps]})


def checkout_report(to_option: str = "opt_exclude_internal") -> Report:
    result = AnalysisResult(estimate=0.1, ci_low=0.0, ci_high=0.2, p_value=0.01, n=10)
    label = {"opt_exclude_internal": "Exclude internal sessions"}.get(
        to_option, "Exclude internal and bot-like sessions"
    )
    change = Change(
        step_id="step_filter_records",
        step_title="Filter records",
        from_option="opt_keep_all",
        to_option=to_option,
        to_label=label,
        rationale="r",
    )
    flip = Flip(
        universe_id="u1",
        changes=[change],
        baseline_result=result,
        flipped_result=result,
        baseline_verdict="SHIP",
        flipped_verdict="DON'T SHIP",
    )
    return Report(
        question="Q?",
        original_verdict="SHIP",
        original_result=result,
        minimal_flip=flip,
        influences=[],
        robustness=0.5,
        n_universes=4,
        n_flipped=1,
    )


def test_sentence_names_step_from_and_to_labels() -> None:
    sentence = flip_sentence(checkout_plan(), checkout_report())
    assert sentence == (
        'The minimal flip changes Filter records from "Keep all sessions" '
        'to "Exclude internal sessions".'
    )


def test_sentence_joins_several_changes() -> None:
    report = checkout_report()
    assert report.minimal_flip is not None
    second = report.minimal_flip.changes[0].model_copy(
        update={"step_title": "Estimator", "step_id": "m1", "from_option": "ols", "to_label": "W"}
    )
    report.minimal_flip.changes.append(second)
    sentence = flip_sentence(checkout_plan(), report)
    assert sentence is not None and 'to "W".' in sentence and '" and Estimator from' in sentence


def test_no_sentence_without_a_flip() -> None:
    report = checkout_report().model_copy(update={"minimal_flip": None})
    assert flip_sentence(checkout_plan(), report) is None
    assert problems(checkout_plan(), report, "anything") == []


def test_has_sentence_ignores_whitespace_only() -> None:
    assert has_sentence("A.  The  minimal flip\nchanges X. B.", "The minimal flip changes X.")
    assert not has_sentence("The minimal flip changed X.", "The minimal flip changes X.")


def test_other_option_of_the_flipped_step_is_detected_across_inflections() -> None:
    plan, report = checkout_plan(), checkout_report()
    text = "The flip works by excluding internal and bot-like sessions from the data."
    assert wrong_labels(plan, report, text) == ["Exclude internal and bot-like sessions"]


def test_the_to_option_and_the_from_option_are_allowed_even_when_nested() -> None:
    plan, report = checkout_plan(), checkout_report("opt_exclude_internal")
    text = "Keep all sessions versus Exclude internal sessions changes the verdict."
    assert wrong_labels(plan, report, text) == []
    both = checkout_report("opt_exclude_both")
    assert wrong_labels(plan, both, "It excludes internal and bot-like sessions.") == []


def test_insert_sentence_goes_second() -> None:
    assert insert_sentence("One. Two. Three.", "S.") == "One. S. Two. Three."
    assert insert_sentence("Only one", "S.") == "Only one S."
