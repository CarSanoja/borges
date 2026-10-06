from __future__ import annotations

from pathlib import Path

from borges.runs.inputs import ResolvedRun
from borges.runs.orchestrator_meta import new_run_meta
from tests.runs.fakes import RULE


def resolved() -> ResolvedRun:
    return ResolvedRun(
        case_id="demo",
        title="Demo case",
        question="q",
        decision_rule=RULE,
        dataset_name="d",
        data=b"",
        max_universes=5,
        fixtures_dir=Path("."),
    )


def test_new_run_meta_describes_the_run_and_its_owner_process() -> None:
    meta = new_run_meta(resolved(), "scripted", "local", "queued", {"principal": "caller://a"})
    assert meta["status"] == "queued" and meta["case_id"] == "demo"
    assert meta["llm"] == "scripted" and meta["backend"] == "local"
    assert meta["principal"] == "caller://a" and "owner_pid" in meta and "owner_host" in meta
    assert meta["verdict"] is None and meta["n_universes"] == 0


def test_extra_fields_cannot_be_forgotten_and_default_to_none() -> None:
    meta = new_run_meta(resolved(), "nebius", "contree", "running")
    assert meta["status"] == "running" and "principal" not in meta


def test_outcome_meta_counts_started_and_failed_universes() -> None:
    from types import SimpleNamespace

    from borges.garden.models import Garden, Universe
    from borges.runs.orchestrator_meta import outcome_meta

    garden = Garden()
    for uid, status in (("a", "done"), ("b", "failed"), ("c", "failed")):
        garden.add(Universe(id=uid, choices={}, kind="single", status=status))
    llm = SimpleNamespace(totals=SimpleNamespace(cost_usd=0.5))
    pipeline = SimpleNamespace(report=None, flip=None, garden=garden, llm=llm)
    meta = outcome_meta(pipeline)
    assert meta["n_universes"] == 3
    assert meta["n_failed"] == 2
