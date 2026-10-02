from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from borges.analysis import code_guard
from borges.analysis.models import AnalysisResult, DecisionRule
from borges.analysis.schemas import (
    AdversaryOutput,
    CoderOutput,
    JudgeOutput,
    NarratorOutput,
    PlannerOutput,
)
from borges.cases.models import CaseSpec

CASE_DIR = Path(__file__).resolve().parents[2] / "cases" / "checkout_ab"
FIXTURES = CASE_DIR / "fixtures"
STEP_ORDER = ["internal_traffic", "bot_filter", "novelty_window", "unit", "model"]
DEFAULTS = {
    "internal_traffic": "keep_all",
    "bot_filter": "none",
    "novelty_window": "all_days",
    "unit": "sessions",
    "model": "two_prop_z",
}
FLIP = ("internal_traffic", "exclude_internal")
ACCEPTED = ("model", "adv_ols_cluster_user")
REJECTED = ("bot_filter", "adv_engaged_only")


def load(key: str) -> dict:
    return json.loads((FIXTURES / (key.replace(":", "__") + ".json")).read_text())


def planner() -> PlannerOutput:
    return PlannerOutput.model_validate(load("planner")["parsed"])


def coder_code(step_id: str, option_id: str) -> str:
    return CoderOutput.model_validate(load(f"coder:{step_id}.{option_id}")["parsed"]).code


def run_universe(frame: pd.DataFrame, choices: dict[str, str]) -> AnalysisResult:
    ctx: dict = {}
    data = frame.copy()
    for step_id in STEP_ORDER:
        namespace: dict = {}
        exec(coder_code(step_id, choices[step_id]), namespace)
        if step_id == "model":
            return AnalysisResult(**namespace["estimate"](data, ctx))
        data = namespace["apply"](data, ctx)
    raise AssertionError("no model step")


@pytest.fixture(scope="module")
def case() -> CaseSpec:
    return CaseSpec.model_validate_json((CASE_DIR / "case.json").read_text())


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    return pd.read_parquet(CASE_DIR / "data.parquet")


@pytest.fixture(scope="module")
def universes(frame: pd.DataFrame) -> dict[tuple[str, str] | None, AnalysisResult]:
    results: dict[tuple[str, str] | None, AnalysisResult] = {None: run_universe(frame, DEFAULTS)}
    for step in planner().steps:
        for option in step.options:
            if not option.is_default:
                results[(step.id, option.id)] = run_universe(
                    frame, {**DEFAULTS, step.id: option.id}
                )
    results[ACCEPTED] = run_universe(frame, {**DEFAULTS, ACCEPTED[0]: ACCEPTED[1]})
    return results


def test_case_spec(case: CaseSpec) -> None:
    assert case.id == "checkout_ab"
    assert case.decision_rule.positive_label == "SHIP"
    assert case.decision_rule.negative_label == "DON'T SHIP"
    assert case.max_universes == 40
    assert case.dataset_name == "checkout_sessions"


def test_dataset_shape(frame: pd.DataFrame) -> None:
    assert (CASE_DIR / "data.parquet").stat().st_size < 2_000_000
    assert 28_000 <= len(frame) <= 32_000
    assert list(frame.columns) == [
        "session_id",
        "user_id",
        "day",
        "variant",
        "platform",
        "is_internal",
        "session_seconds",
        "converted",
        "revenue",
    ]
    assert frame["session_id"].is_unique
    assert frame["day"].between(0, 13).all()
    assert frame.groupby("user_id")["variant"].nunique().max() == 1
    assert frame.groupby("user_id").size().between(1, 4).all()
    assert (frame.loc[frame["converted"] == 0, "revenue"] == 0).all()
    shares = frame["platform"].value_counts(normalize=True)
    assert shares["web"] == pytest.approx(0.55, abs=0.03)
    assert shares["ios"] == pytest.approx(0.30, abs=0.03)


def test_dataset_story(frame: pd.DataFrame) -> None:
    internal = frame[frame["is_internal"]]
    assert 0.009 <= frame["is_internal"].mean() <= 0.015
    assert (internal["variant"] == "treatment").mean() > 0.7
    assert 0.5 <= internal["converted"].mean() <= 0.7
    bots = frame[frame["session_seconds"] < 2]
    assert 0.02 <= len(bots) / len(frame) <= 0.04
    assert bots["converted"].sum() == 0
    assert bots["variant"].eq("treatment").mean() == pytest.approx(0.5, abs=0.1)
    assert 0.03 <= frame["converted"].mean() <= 0.036


def test_plan_structure() -> None:
    plan = planner()
    assert [s.id for s in plan.steps] == STEP_ORDER
    assert [s.kind for s in plan.steps] == ["filter", "filter", "filter", "transform", "model"]
    for step in plan.steps:
        defaults = [o.id for o in step.options if o.is_default]
        assert defaults == [DEFAULTS[step.id]]
        assert len(step.options) == 2


def test_baseline_ships(
    case: CaseSpec, universes: dict[tuple[str, str] | None, AnalysisResult]
) -> None:
    baseline = universes[None]
    assert case.decision_rule.label(baseline) == "SHIP"
    assert 0.005 < baseline.p_value < 0.04
    assert baseline.ci_low < baseline.estimate < baseline.ci_high


def test_exclude_internal_flips_with_largest_move(
    case: CaseSpec, universes: dict[tuple[str, str] | None, AnalysisResult]
) -> None:
    baseline = universes[None]
    assert case.decision_rule.label(universes[FLIP]) == "DON'T SHIP"
    moves = {
        key: abs(result.estimate - baseline.estimate)
        for key, result in universes.items()
        if key is not None
    }
    assert max(moves, key=moves.__getitem__) == FLIP


def test_other_flips_keep_ship(
    case: CaseSpec, universes: dict[tuple[str, str] | None, AnalysisResult]
) -> None:
    others = [k for k in universes if k not in (None, FLIP)]
    kept = [k for k in others if case.decision_rule.label(universes[k]) == "SHIP"]
    assert len(kept) >= 2
    assert len(kept) == len(others)


def test_accepted_adversary_option_runs(
    case: CaseSpec, universes: dict[tuple[str, str] | None, AnalysisResult]
) -> None:
    assert case.decision_rule.label(universes[ACCEPTED]) == "SHIP"


def test_rejected_option_is_runnable(frame: pd.DataFrame) -> None:
    result = run_universe(frame, {**DEFAULTS, REJECTED[0]: REJECTED[1]})
    assert result.n < len(frame)


def test_adversary_and_judges() -> None:
    adversary = AdversaryOutput.model_validate(load("adversary")["parsed"])
    assert [(p.step_id, p.id) for p in adversary.proposals] == [ACCEPTED, REJECTED]
    accepted = JudgeOutput.model_validate(load("judge:model.adv_ols_cluster_user")["parsed"])
    rejected = JudgeOutput.model_validate(load("judge:bot_filter.adv_engaged_only")["parsed"])
    assert accepted.accepted and accepted.defensibility >= 0.6
    assert not rejected.accepted and rejected.defensibility < 0.6


def test_fixture_envelopes() -> None:
    files = sorted(FIXTURES.glob("*.json"))
    assert len(files) == 22
    for path in files:
        record = json.loads(path.read_text())
        assert set(record) == {"model", "text", "parsed", "tokens_in", "tokens_out"}
        assert json.loads(record["text"]) == record["parsed"]
        assert record["tokens_in"] == 0 and record["tokens_out"] == 0
        assert record["model"] == "scripted"


def test_narrator_numbers_match_validation(
    case: CaseSpec,
    frame: pd.DataFrame,
    universes: dict[tuple[str, str] | None, AnalysisResult],
) -> None:
    narrator = NarratorOutput.model_validate(load("narrator")["parsed"])
    baseline, flip = universes[None], universes[FLIP]
    for result in (baseline, flip):
        assert f"{result.estimate:+.2f} pp" in narrator.narrative
        assert f"p = {result.p_value:.3f}" in narrator.narrative
        assert f"{result.n:,} sessions" in narrator.narrative
    assert f"{int(frame['is_internal'].sum()):,} sessions" in narrator.narrative
    assert case.decision_rule.label(baseline) in narrator.narrative
    assert narrator.caveats


def test_decision_rule_label_direction() -> None:
    rule = DecisionRule(metric="m")
    assert (
        rule.label(AnalysisResult(estimate=0.5, ci_low=0, ci_high=1, p_value=0.01, n=1)) == "SHIP"
    )


def test_all_code_passes_guard() -> None:
    kinds = {s.id: s.kind for s in planner().steps}
    for path in FIXTURES.glob("coder__*.json"):
        step_id = path.stem.removeprefix("coder__").split(".")[0]
        code = CoderOutput.model_validate(json.loads(path.read_text())["parsed"]).code
        try:
            problems = code_guard.check_code(code, kinds[step_id])
        except NotImplementedError:
            pytest.skip("code_guard not implemented yet")
        assert problems == []
