from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from borges.analysis.models import AnalysisPlan, DecisionRule, Option
from borges.fleet.models import RunAgents
from borges.garden.models import Flip, Report, Universe
from borges.runs.events import Event, MemoryUsedData
from borges.runs.models import CheckpointNode, RunSnapshot, UsageSnapshot


def _upsert_option(plan: AnalysisPlan | None, step_id: str, option: Option) -> None:
    if plan is None:
        return
    step = next((s for s in plan.steps if s.id == step_id), None)
    if step is None:
        return
    for index, existing in enumerate(step.options):
        if existing.id == option.id:
            step.options[index] = option
            return
    step.options.append(option)


def _judge_option(plan: AnalysisPlan | None, data: dict[str, Any]) -> None:
    if plan is None:
        return
    for step in plan.steps:
        if step.id != data["step_id"]:
            continue
        for option in step.options:
            if option.id == data["option_id"]:
                option.defensibility = data["defensibility"]


def _apply_universe(snapshot: RunSnapshot, data: dict[str, Any]) -> None:
    universe = Universe.model_validate(data["universe"])
    snapshot.garden.add(universe)
    if universe.kind == "baseline":
        snapshot.garden.baseline_id = universe.id


def _apply(snapshot: RunSnapshot, event: Event) -> None:
    data = event.data
    match event.type:
        case "run.started":
            snapshot.case_id = data.get("case_id")
            snapshot.title = data.get("title", "")
            snapshot.question = data.get("question", "")
            snapshot.decision_rule = DecisionRule.model_validate(data["decision_rule"])
            snapshot.llm = data.get("llm")
            snapshot.backend = data.get("backend")
            if data.get("agents"):
                snapshot.agents = RunAgents.model_validate(data["agents"])
        case "run.resumed":
            snapshot.resumed += 1
        case "memory.used":
            snapshot.memory = MemoryUsedData.model_validate(data)
        case "stage":
            snapshot.stages[data["name"]] = data["status"]
        case "plan.ready":
            snapshot.plan = AnalysisPlan.model_validate(data["plan"])
        case "option.proposed":
            _upsert_option(snapshot.plan, data["step_id"], Option.model_validate(data["option"]))
        case "option.judged":
            _judge_option(snapshot.plan, data)
        case "checkpoint.created":
            snapshot.checkpoints.append(
                CheckpointNode.model_validate({k: data.get(k) for k in CheckpointNode.model_fields})
            )
        case "universe.started" | "universe.finished":
            _apply_universe(snapshot, data)
        case "flip.found" | "flip.verified":
            snapshot.flip = Flip.model_validate(data["flip"])
        case "usage":
            snapshot.usage = UsageSnapshot.model_validate(data)
        case "report.ready":
            snapshot.report = Report.model_validate(data["report"])
        case "run.finished":
            snapshot.status = data["status"]
        case "run.cancelled":
            snapshot.status = "cancelled"
        case "run.failed":
            snapshot.status = "failed"
            snapshot.error = data.get("error")


def fold(events: Iterable[Event], run_id: str | None = None) -> RunSnapshot:
    """Reduce an event stream to the current run state. The UI applies the same rules."""
    snapshot = RunSnapshot(run_id=run_id or "")
    for event in events:
        if not snapshot.run_id:
            snapshot.run_id = event.run_id
        _apply(snapshot, event)
        snapshot.last_seq = max(snapshot.last_seq, event.seq)
    return snapshot
