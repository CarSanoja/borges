from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from borges.bench.blade_report import write_outputs
from borges.bench.blade_runner import adversary_disabled
from borges.bench.blade_suite import BenchConfig, BenchResult, run_benchmark
from borges.config import REPO_ROOT, Settings
from tests.bench.support import MINI, FakeMatcher

pytestmark = pytest.mark.timeout(1200)


@pytest.fixture(scope="module")
def outcome(tmp_path_factory) -> tuple[BenchResult, FakeMatcher, Path]:
    out = tmp_path_factory.mktemp("bench")
    config = BenchConfig(
        datasets=["hurricane", "teachingratings"],
        arms=["planner", "adversary"],
        llm="scripted",
        out=out,
        blade_dir=MINI,
        max_universes=24,
        settings=Settings(_env_file=None, borges_cases_dir=REPO_ROOT / "cases"),
    )
    matcher = FakeMatcher()
    import asyncio

    result = asyncio.run(run_benchmark(config, matcher, False))
    write_outputs(result, matcher.name)
    return result, matcher, out


def arm(result: BenchResult, dataset: str, name: str):
    return next(a for a in result.arms if a.dataset == dataset and a.arm == name)


def test_every_dataset_and_arm_is_scored(outcome) -> None:
    result, matcher, _ = outcome
    assert [(a.dataset, a.arm) for a in result.arms] == [
        ("hurricane", "planner"),
        ("hurricane", "adversary"),
        ("teachingratings", "planner"),
        ("teachingratings", "adversary"),
    ]
    assert all(a.analyses and a.metrics and not a.errors for a in result.arms)
    assert matcher.seen.count("cvar") == 4
    assert result.total_cost == pytest.approx(0.012)


def test_adversary_arm_explores_the_adversary_option_and_planner_arm_does_not(outcome) -> None:
    result, _, _ = outcome
    for dataset in ("hurricane", "teachingratings"):
        planner = arm(result, dataset, "planner")
        full = arm(result, dataset, "adversary")
        assert not any(a.kind == "adversary" for a in planner.analyses)
        assert any(a.kind == "adversary" for a in full.analyses)
        assert len(full.analyses) >= len(planner.analyses)


def test_hurricane_metrics_come_from_the_fake_matcher_rules(outcome) -> None:
    result, _, _ = outcome
    metrics = arm(result, "hurricane", "adversary").metrics
    assert metrics["cvar"]["n_expert"] == 4 and metrics["cvar"]["matched_expert"] == 3
    assert metrics["model"]["matched_expert"] == 3
    assert metrics["transform"]["matched_expert"] == 1
    assert 0 < metrics["cvar"]["hit_rate"] <= 1


def test_analyses_are_distinct_and_have_runnable_looking_code(outcome) -> None:
    result, _, _ = outcome
    for a in result.arms:
        signatures = [x.signature for x in a.analyses]
        assert len(signatures) == len(set(signatures))
        for analysis in a.analyses:
            ast.parse(analysis.transform_code)
            ast.parse(analysis.m_code)
            assert "def transform(df)" in analysis.transform_code
            assert "def model(df" in analysis.m_code


def test_cvars_are_read_off_the_executed_code(outcome) -> None:
    result, _, _ = outcome
    hurricane = arm(result, "hurricane", "planner").analyses
    ivs = {tuple(a.cvars.ivs[0].columns) for a in hurricane}
    assert ivs == {("masfem",), ("gender_mf",), ("masfem_mturk",)}
    assert all(a.cvars.dv.columns == ["alldeaths"] for a in hurricane)
    controls = {c.columns[0] for a in hurricane for c in a.cvars.controls}
    assert {"ndam15", "min", "wind", "category"} <= controls
    teaching = arm(result, "teachingratings", "planner").analyses
    assert all(a.cvars.ivs[0].columns == ["beauty"] for a in teaching)
    assert all(a.cvars.dv.columns == ["eval"] for a in teaching)


def test_outputs_follow_the_blade_submission_format(outcome) -> None:
    _, _, out = outcome
    payload = json.loads((out / "submissions" / "hurricane__adversary.json").read_text())
    assert payload["dataset_name"] == "hurricane"
    first = payload["analyses"][0]
    assert set(first) == {"cvars", "transform_code", "m_code"}
    assert set(first["cvars"]) == {"ivs", "dv", "controls"}
    assert set(first["cvars"]["ivs"][0]) == {"description", "columns"}
    assert set(first["cvars"]["controls"][0]) == {
        "description",
        "columns",
        "is_moderator",
        "moderator_on",
    }


def test_summary_files_carry_provenance_and_the_table(outcome) -> None:
    _, _, out = outcome
    summary = json.loads((out / "summary.json").read_text())
    assert summary["llm"] == "scripted" and summary["matcher"] == "fake"
    assert summary["arms"] == ["planner", "adversary"]
    assert "Apache-2.0" in summary["attribution"] and summary["method"]
    row = next(r for r in summary["rows"] if r["dataset"] == "hurricane" and r["arm"] == "planner")
    assert set(row["metrics"]) == {"cvar", "model", "transform"}
    assert row["run_ids"] and row["mean_f1"] >= 0
    table = (out / "summary.md").read_text()
    assert "| hurricane | planner |" in table and "| teachingratings | adversary |" in table
    assert "cvar cov" in table and "Method" in table


def test_run_directories_keep_only_events_and_meta(outcome) -> None:
    _, _, out = outcome
    run_dirs = list((out / "runs" / "hurricane" / "planner").iterdir())
    assert run_dirs
    assert {p.name for p in run_dirs[0].iterdir()} <= {"events.jsonl", "meta.json"}


def test_adversary_switch_is_restored_after_use() -> None:
    from borges.runs import pipeline_search

    original = pipeline_search.run_adversary
    with adversary_disabled():
        assert pipeline_search.run_adversary is not original
    assert pipeline_search.run_adversary is original
