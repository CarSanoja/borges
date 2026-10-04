from __future__ import annotations

from typing import Any

from borges.analysis.models import AnalysisResult
from borges.garden.models import Change, Flip, Report, Universe
from borges.runs.events import Event
from borges.runs.state import fold
from tests.runs.fakes import RULE, adversary_proposal, make_plan

RESULT = AnalysisResult(estimate=1.0, ci_low=0.5, ci_high=1.5, p_value=0.01, n=10)


def evt(seq: int, event_type: str, data: dict[str, Any]) -> Event:
    return Event(seq=seq, ts=float(seq), run_id="r_1", type=event_type, data=data)


def universe(uid: str, kind: str = "single", status: str = "done") -> dict[str, Any]:
    value = Universe(
        id=uid, choices={"s1": "a"}, kind=kind, status=status, result=RESULT, verdict="SHIP"
    )
    return {"universe": value.model_dump(mode="json")}


def plan_data() -> dict[str, Any]:
    return {"plan": make_plan().model_dump(mode="json")}


def flip() -> Flip:
    return Flip(
        universe_id="u1",
        changes=[
            Change(
                step_id="s1",
                step_title="t",
                from_option="a",
                to_option="b",
                to_label="l",
                rationale="r",
            )
        ],
        baseline_result=RESULT,
        flipped_result=RESULT,
        baseline_verdict="SHIP",
        flipped_verdict="DON'T SHIP",
    )


def test_empty_stream_is_a_running_snapshot() -> None:
    snapshot = fold([], "r_1")
    assert snapshot.status == "running" and snapshot.last_seq == 0 and snapshot.run_id == "r_1"


def test_run_started_and_stages() -> None:
    started = {
        "case_id": "c",
        "title": "T",
        "question": "Q?",
        "decision_rule": RULE.model_dump(mode="json"),
        "llm": "nebius",
        "backend": "contree",
    }
    snapshot = fold(
        [
            evt(1, "run.started", started),
            evt(2, "stage", {"name": "planning", "status": "started"}),
            evt(3, "stage", {"name": "planning", "status": "done"}),
        ]
    )
    assert (snapshot.run_id, snapshot.case_id, snapshot.title) == ("r_1", "c", "T")
    assert snapshot.question == "Q?" and snapshot.decision_rule == RULE
    assert snapshot.stages == {"planning": "done"} and snapshot.last_seq == 3
    assert (snapshot.llm, snapshot.backend) == ("nebius", "contree")


def test_plan_ready_replaces_plan() -> None:
    changed = make_plan()
    changed.steps.pop()
    snapshot = fold(
        [evt(1, "plan.ready", plan_data()), evt(2, "plan.ready", {"plan": changed.model_dump()})]
    )
    assert [s.id for s in snapshot.plan.steps] == ["s1"]


def test_proposed_and_judged_options() -> None:
    proposal = adversary_proposal()
    snapshot = fold(
        [
            evt(1, "plan.ready", plan_data()),
            evt(2, "option.proposed", {"step_id": "s2", "option": proposal.option.model_dump()}),
            evt(
                3,
                "option.judged",
                {
                    "step_id": "s2",
                    "option_id": "adv",
                    "defensibility": 0.7,
                    "accepted": True,
                    "reason": "ok",
                },
            ),
            evt(
                4,
                "option.judged",
                {
                    "step_id": "s2",
                    "option_id": "ghost",
                    "defensibility": 0.1,
                    "accepted": False,
                    "reason": "no",
                },
            ),
        ]
    )
    options = snapshot.plan.step("s2").options
    assert [o.id for o in options] == ["x", "y", "adv"]
    assert options[2].defensibility == 0.7 and options[0].defensibility is None


def test_proposed_before_plan_is_ignored() -> None:
    proposal = adversary_proposal()
    snapshot = fold(
        [evt(1, "option.proposed", {"step_id": "s2", "option": proposal.option.model_dump()})]
    )
    assert snapshot.plan is None


def test_checkpoints_universes_and_baseline() -> None:
    snapshot = fold(
        [
            evt(
                1,
                "checkpoint.created",
                {
                    "checkpoint_id": "cp0",
                    "parent_id": None,
                    "step_id": None,
                    "option_id": None,
                    "depth": 0,
                    "duration_s": 0.1,
                },
            ),
            evt(
                2,
                "checkpoint.created",
                {
                    "checkpoint_id": "cp1",
                    "parent_id": "cp0",
                    "step_id": "s1",
                    "option_id": "a",
                    "depth": 1,
                },
            ),
            evt(3, "universe.started", universe("u0", "baseline", "running")),
            evt(4, "universe.finished", universe("u0", "baseline")),
            evt(5, "universe.finished", universe("u1")),
        ]
    )
    assert [c.checkpoint_id for c in snapshot.checkpoints] == ["cp0", "cp1"]
    assert snapshot.checkpoints[1].parent_id == "cp0" and snapshot.checkpoints[1].depth == 1
    assert snapshot.garden.baseline_id == "u0"
    assert snapshot.garden.universes["u0"].status == "done"
    assert set(snapshot.garden.universes) == {"u0", "u1"}


def test_flip_usage_report_and_finish() -> None:
    found = flip()
    verified = found.model_copy(update={"reproduced": True})
    report = Report(
        question="q",
        original_verdict="SHIP",
        original_result=RESULT,
        minimal_flip=verified,
        influences=[],
        robustness=0.5,
        n_universes=3,
        n_flipped=1,
        narrative="n",
    )
    usage = {
        "tokens_in": 1,
        "tokens_out": 2,
        "cost_usd": 0.1,
        "llm_calls": 3,
        "cached_calls": 0,
        "checkpoints": 4,
        "universes": 5,
    }
    events = [
        evt(1, "flip.found", {"flip": found.model_dump(mode="json")}),
        evt(2, "usage", usage),
        evt(3, "flip.verified", {"flip": verified.model_dump(mode="json")}),
        evt(4, "report.ready", {"report": report.model_dump(mode="json")}),
        evt(5, "run.finished", {"status": "completed", "elapsed_s": 1.0}),
    ]
    snapshot = fold(events)
    assert snapshot.flip.reproduced is True
    assert snapshot.usage.universes == 5 and snapshot.usage.cost_usd == 0.1
    assert snapshot.report.narrative == "n"
    assert snapshot.status == "completed"
    assert fold(events[:1]).flip.reproduced is None


def test_run_failed_then_finished_failed() -> None:
    snapshot = fold(
        [
            evt(1, "run.failed", {"error": "boom"}),
            evt(2, "run.finished", {"status": "failed", "elapsed_s": 0.1}),
        ]
    )
    assert snapshot.status == "failed" and snapshot.error == "boom"


def test_last_seq_is_the_maximum() -> None:
    snapshot = fold(
        [
            evt(7, "stage", {"name": "coding", "status": "started"}),
            evt(3, "stage", {"name": "coding", "status": "done"}),
        ]
    )
    assert snapshot.last_seq == 7


def test_resumed_events_are_counted() -> None:
    snapshot = fold(
        [
            evt(1, "stage", {"name": "coding", "status": "started"}),
            evt(2, "run.resumed", {"reason": "restart", "attempt": 1}),
            evt(3, "run.resumed", {"reason": "retry", "attempt": 2}),
        ]
    )
    assert snapshot.resumed == 2 and snapshot.status == "running"


def test_a_cancelled_run_ends_cancelled() -> None:
    snapshot = fold(
        [
            evt(1, "run.cancelled", {"reason": "by request"}),
            evt(2, "run.finished", {"status": "cancelled", "elapsed_s": 1.0}),
        ]
    )
    assert snapshot.status == "cancelled" and snapshot.error is None


def test_a_step_replanned_event_is_tolerated_by_the_fold() -> None:
    replanned = {"step_id": "s1", "failed_option_ids": ["a"], "new_option_ids": ["b"]}
    events = [evt(1, "plan.ready", plan_data()), evt(2, "step.replanned", replanned)]
    snapshot = fold(events)
    assert snapshot.last_seq == 2 and snapshot.plan is not None and snapshot.status == "running"
