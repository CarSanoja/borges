from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from borges.analysis.models import (
    AnalysisPlan,
    DatasetProfile,
    DecisionRule,
    Option,
    Proposal,
    Step,
)
from borges.cases.models import CaseSpec
from borges.cases.registry import CaseRegistry
from borges.config import Settings
from borges.llm.client import UsageTotals
from borges.runs.bus import EventBus
from borges.runs.events import Event
from borges.runs.orchestrator import RunOrchestrator
from borges.runs.store import RunStore

BASE_ESTIMATE = 1.0
RULE = DecisionRule(metric="diff", threshold=0.0)


def make_option(option_id: str, default: bool = False) -> Option:
    return Option(
        id=option_id,
        label=f"label {option_id}",
        rationale=f"why {option_id}",
        spec=f"spec {option_id}",
        is_default=default,
    )


def make_plan() -> AnalysisPlan:
    return AnalysisPlan(
        question="does it ship?",
        estimand="mean diff",
        decision_rule=RULE,
        dataset=DatasetProfile(name="d", n_rows=3, columns=[]),
        steps=[
            Step(
                id="s1",
                title="Filter",
                kind="filter",
                description="",
                options=[make_option("a", True), make_option("b")],
            ),
            Step(
                id="s2",
                title="Model",
                kind="model",
                description="",
                options=[make_option("x", True), make_option("y")],
            ),
        ],
    )


class FakeLLM:
    def __init__(self) -> None:
        self.totals = UsageTotals(tokens_in=10, tokens_out=5, cost_usd=0.01, calls=2)


class FakeBackend:
    name = "fake"

    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def parquet_bytes() -> bytes:
    buffer = io.BytesIO()
    pd.DataFrame({"a": [1, 2, 3]}).to_parquet(buffer)
    return buffer.getvalue()


def adversary_proposal(step_id: str = "s2", option_id: str = "adv") -> Proposal:
    option = make_option(option_id).model_copy(update={"origin": "adversary"})
    return Proposal(step_id=step_id, option=option)


def write_case(cases_dir: Path, case_id: str = "demo", with_recording: bool = False) -> None:
    folder = cases_dir / case_id
    (folder / "fixtures").mkdir(parents=True)
    (folder / "data.parquet").write_bytes(parquet_bytes())
    spec = CaseSpec(
        id=case_id,
        title="Demo case",
        subtitle="sub",
        question="does it ship?",
        decision_rule=RULE,
        dataset_name="demo data",
        max_universes=10,
    )
    (folder / "case.json").write_text(spec.model_dump_json())
    if with_recording:
        (folder / "recorded").mkdir()
        event = Event(seq=1, ts=1.0, run_id="r", type="stage", data={"name": "profiling"})
        (folder / "recorded" / "events.jsonl").write_text(event.model_dump_json() + "\n")


@dataclass
class Rig:
    orchestrator: RunOrchestrator
    store: RunStore
    bus: EventBus
    llm: FakeLLM
    backend: FakeBackend
    factory_calls: list[dict[str, Any]]


def make_rig(tmp_path: Path) -> Rig:
    settings = Settings(
        _env_file=None,
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=tmp_path / "cases",
    )
    write_case(settings.borges_cases_dir)
    store = RunStore(settings.borges_runs_dir)
    bus = EventBus(store)
    llm, backend = FakeLLM(), FakeBackend()
    factory_calls: list[dict[str, Any]] = []

    def llm_factory(settings: Settings, mode: Any = None, **kwargs: Any) -> FakeLLM:
        factory_calls.append({"mode": mode, **kwargs})
        return llm

    orchestrator = RunOrchestrator(
        settings,
        store,
        bus,
        CaseRegistry(settings.borges_cases_dir),
        llm_factory=llm_factory,
        backend_factory=lambda settings, kind=None: backend,
    )
    return Rig(orchestrator, store, bus, llm, backend, factory_calls)
