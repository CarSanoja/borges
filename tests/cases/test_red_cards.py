from __future__ import annotations

import json
import sys
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

pytestmark = pytest.mark.timeout(900)

CASE_DIR = Path(__file__).resolve().parents[2] / "cases" / "red_cards"
sys.path.insert(0, str(CASE_DIR))

from validation import (  # noqa: E402
    DEFAULTS,
    STEP_ORDER,
    all_universes,
    changed_steps,
    fixture_path,
    load_codes,
    run_universe,
)

TEAM_RANGE = (0.89, 2.93)
PLANNER_OPTIONS = {
    "skin_tone": ["mean_raters", "rater1_only", "rater2_only", "extremes_only"],
    "exclusions": ["rated_only", "rated_frequent_refs"],
    "covariates": ["none", "physique", "full"],
    "model": ["binomial_glm", "poisson_offset", "binomial_cluster"],
}
ACCEPTED = {"covariates": "adv_full_plus_bias"}
REJECTED = {"exclusions": "adv_low_iat_referees_only"}
FIXTURE_SCHEMAS = {
    "planner": PlannerOutput,
    "adversary": AdversaryOutput,
    "narrator": NarratorOutput,
}


@pytest.fixture(scope="module")
def case() -> CaseSpec:
    return CaseSpec.model_validate_json((CASE_DIR / "case.json").read_text())


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    return pd.read_parquet(CASE_DIR / "data.parquet")


@pytest.fixture(scope="module")
def codes() -> dict[str, str]:
    return load_codes()


@pytest.fixture(scope="module")
def universes(frame, codes, case) -> list[dict]:
    options = {s: list(ids) for s, ids in PLANNER_OPTIONS.items()}
    for step, option_id in {**ACCEPTED, **REJECTED}.items():
        options[step].append(option_id)
    rows = []
    for choices in all_universes(options):
        changes = changed_steps(choices)
        if len(changes) > 2 and not _is_triple_candidate(choices):
            continue
        raw = run_universe(frame, choices, codes)
        result = AnalysisResult(
            **{k: raw[k] for k in ("estimate", "ci_low", "ci_high", "p_value", "n")}
        )
        rows.append(
            {
                "choices": choices,
                "changes": len(changes),
                "result": result,
                "label": case.decision_rule.label(result),
                "rejected": REJECTED["exclusions"] in choices.values(),
            }
        )
    return rows


def _is_triple_candidate(choices: dict[str, str]) -> bool:
    return len(changed_steps(choices)) == 3 and REJECTED["exclusions"] not in choices.values()


def _by_changes(universes: list[dict], n: int, rejected: bool = False) -> list[dict]:
    return [u for u in universes if u["changes"] == n and u["rejected"] == rejected]


def test_every_fixture_validates_against_its_schema():
    paths = sorted((CASE_DIR / "fixtures").glob("*.json"))
    assert len(paths) == 27
    for path in paths:
        payload = json.loads(path.read_text())
        assert set(payload) == {"model", "text", "parsed", "tokens_in", "tokens_out"}
        assert json.loads(payload["text"]) == payload["parsed"]
        assert payload["tokens_in"] == 0 and payload["tokens_out"] == 0
        name = path.stem
        if name.startswith("coder__"):
            CoderOutput.model_validate(payload["parsed"])
        elif name.startswith("judge__"):
            JudgeOutput.model_validate(payload["parsed"])
        else:
            FIXTURE_SCHEMAS[name].model_validate(payload["parsed"])


def test_fixtures_are_labelled_scripted():
    for path in (CASE_DIR / "fixtures").glob("*.json"):
        payload = json.loads(path.read_text())
        assert payload["model"] == "scripted"
        assert "nemotron" not in path.read_text().lower().split('"text"')[0]


def test_plan_has_a_coder_fixture_for_every_option(codes):
    plan = PlannerOutput.model_validate(json.loads(fixture_path("planner").read_text())["parsed"])
    assert [s.id for s in plan.steps] == STEP_ORDER
    planned = {f"{s.id}.{o.id}" for s in plan.steps for o in s.options}
    proposals = AdversaryOutput.model_validate(
        json.loads(fixture_path("adversary").read_text())["parsed"]
    ).proposals
    proposed = {f"{p.step_id}.{p.id}" for p in proposals}
    assert len(proposals) == 2
    assert set(codes) == planned | proposed
    defaults = {s.id: next(o.id for o in s.options if o.is_default) for s in plan.steps}
    assert defaults == DEFAULTS


def test_judgements_accept_one_and_reject_one():
    accepted = JudgeOutput.model_validate(
        json.loads(fixture_path("judge:covariates.adv_full_plus_bias").read_text())["parsed"]
    )
    rejected = JudgeOutput.model_validate(
        json.loads(fixture_path("judge:exclusions.adv_low_iat_referees_only").read_text())["parsed"]
    )
    assert accepted.accepted and accepted.defensibility >= 0.6
    assert not rejected.accepted and rejected.defensibility < 0.6


def test_code_passes_the_guard_when_implemented(codes):
    for key, code in codes.items():
        kind = "model" if key.startswith("model.") else "feature"
        try:
            problems = code_guard.check_code(code, kind)
        except NotImplementedError:
            pytest.skip("code_guard not implemented yet")
        assert problems == [], key
        assert ("def estimate(" in code) == (kind == "model")


def test_case_spec_matches_the_brief(case):
    assert case.id == "red_cards"
    assert case.max_universes == 48
    assert case.decision_rule.positive_label == "BIAS DETECTED"
    assert len(case.reference) == 29
    assert case.reference_label == "29 human research teams (Silberzahn et al., 2018)"
    estimates = [r.estimate for r in case.reference]
    assert (min(estimates), max(estimates)) == pytest.approx(TEAM_RANGE, abs=0.005)
    assert all(r.significant == (r.ci_low > 1) for r in case.reference)


def test_baseline_detects_bias(universes, case):
    (baseline,) = _by_changes(universes, 0)
    result = baseline["result"]
    assert baseline["label"] == "BIAS DETECTED"
    assert result.estimate == pytest.approx(1.337, abs=0.002)
    assert result.p_value < 0.001
    assert result.n == 124621
    assert case.decision_rule.is_positive(result)


def test_no_single_flip_changes_the_verdict(universes):
    singles = _by_changes(universes, 1)
    assert len(singles) == 9
    assert {u["label"] for u in singles} == {"BIAS DETECTED"}
    estimates = [u["result"].estimate for u in singles]
    assert min(estimates) == pytest.approx(1.27, abs=0.005)
    assert max(estimates) == pytest.approx(1.356, abs=0.005)


def test_no_pair_changes_the_verdict(universes):
    pairs = _by_changes(universes, 2)
    assert len(pairs) == 29
    assert {u["label"] for u in pairs} == {"BIAS DETECTED"}


def test_the_verdict_first_changes_at_three_changes(universes):
    flipped = [u for u in _by_changes(universes, 3) if u["label"] == "NO CLEAR EVIDENCE"]
    found = {tuple(u["choices"][s] for s in STEP_ORDER) for u in flipped}
    assert found == {
        ("mean_raters", "rated_frequent_refs", "full", "binomial_cluster"),
        ("rater2_only", "rated_only", "full", "binomial_cluster"),
        ("rater2_only", "rated_only", "adv_full_plus_bias", "binomial_cluster"),
        ("rater2_only", "rated_frequent_refs", "full", "binomial_glm"),
    }
    assert all(0.05 <= u["result"].p_value < 0.07 for u in flipped)


def test_rejected_option_is_the_only_single_flip(universes):
    (rejected,) = _by_changes(universes, 1, rejected=True)
    assert rejected["label"] == "NO CLEAR EVIDENCE"
    assert rejected["result"].estimate == pytest.approx(1.252, abs=0.002)
    assert rejected["result"].p_value == pytest.approx(0.066, abs=0.002)


def test_estimates_sit_inside_the_human_teams_range(universes):
    usable = [u for u in universes if not u["rejected"]]
    for u in usable:
        assert TEAM_RANGE[0] <= u["result"].estimate <= TEAM_RANGE[1]
        assert u["result"].ci_low <= u["result"].estimate <= u["result"].ci_high


def test_narrator_numbers_match_the_validation(universes, case):
    narrative = NarratorOutput.model_validate(
        json.loads(fixture_path("narrator").read_text())["parsed"]
    ).narrative
    (baseline,) = _by_changes(universes, 0)
    result = baseline["result"]
    assert f"OR {result.estimate:.2f}" in narrative
    assert f"{result.n:,}" in narrative
    assert "BIAS DETECTED" in narrative and "NO CLEAR EVIDENCE" in narrative
    rule = DecisionRule.model_validate(
        json.loads((CASE_DIR / "case.json").read_text())["decision_rule"]
    )
    assert rule.label(result) == "BIAS DETECTED"
