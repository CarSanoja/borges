from __future__ import annotations

import json
import re

import pytest

from borges.analysis.models import AnalysisResult
from tests.cases.marp_support import (
    CASE_IDS,
    CASES_DIR,
    WB_OVERALL,
    case_frame,
    case_spec,
    changed_steps,
    defaults,
    option_codes,
    option_ids,
    read_grid,
    recorded,
    run_universe,
)


def _estimate(rq, choices, codes=None):
    raw = run_universe(case_frame(rq), rq, choices, codes)
    return AnalysisResult(**{k: raw[k] for k in ("estimate", "ci_low", "ci_high", "p_value", "n")})


def test_every_option_has_code_and_a_fixture():
    for rq in (1, 2):
        fixtures = CASES_DIR / CASE_IDS[rq] / "fixtures"
        planned = {f"{s}.{o}" for s, ids in option_ids(rq).items() for o in ids}
        assert planned == set(option_codes(rq))
        on_disk = {p.stem.removeprefix("coder__") for p in fixtures.glob("coder__*.json")}
        assert on_disk == planned
        for key, code in option_codes(rq).items():
            payload = json.loads((fixtures / f"coder__{key}.json").read_text())
            assert payload["parsed"]["code"] == code


def test_baselines_on_the_real_data():
    first = _estimate(1, defaults(1))
    assert first.estimate == pytest.approx(0.140, abs=0.001)
    assert first.ci_low > 0.11 and first.p_value < 1e-30 and first.n == 10535
    second = _estimate(2, defaults(2))
    assert second.estimate == pytest.approx(0.045, abs=0.001)
    assert second.ci_low > 0.02 and second.p_value < 0.001


def test_pooled_ols_is_the_single_fragile_choice_for_norms():
    flipped = _estimate(2, {**defaults(2), "model": "ols_pooled"})
    assert flipped.estimate == pytest.approx(0.018, abs=0.001)
    assert flipped.estimate > 0 and flipped.p_value == pytest.approx(0.056, abs=0.002)
    assert flipped.ci_low < 0 < flipped.ci_high
    rule = case_spec(2).decision_rule
    assert rule.label(flipped) == "NO CLEAR EVIDENCE"
    assert rule.label(_estimate(2, defaults(2))) == "DEPENDS ON NORMS"


def test_each_case_keeps_the_estimate_on_the_documented_term():
    for rq in (1, 2):
        base = _estimate(rq, defaults(rq))
        other = _estimate(rq, {**defaults(rq), "model": "ols_country_fe"})
        assert base.estimate == pytest.approx(other.estimate, abs=0.01)


def test_physical_facet_is_the_documented_exception_outside_the_option_space():
    codes = {**option_codes(1), "wellbeing.facet": WB_OVERALL.replace("overall", "phys")}
    base = {**defaults(1), "wellbeing": "facet"}
    alone = _estimate(1, base, codes)
    adjusted = _estimate(1, {**base, "covariates": "demographics"}, codes)
    assert alone.estimate == pytest.approx(0.042, abs=0.002) and alone.p_value < 0.001
    assert adjusted.estimate == pytest.approx(0.017, abs=0.002)
    assert adjusted.p_value == pytest.approx(0.087, abs=0.005)


def test_full_grid_summaries():
    religiosity = read_grid(CASES_DIR / CASE_IDS[1])
    assert religiosity["n_universes"] == 768 and religiosity["n_flipped"] == 0
    assert religiosity["estimate_min"] > 0.05 and religiosity["estimate_max"] < 0.16
    norms = read_grid(CASES_DIR / CASE_IDS[2])
    assert norms["n_universes"] == 1536 and norms["n_flipped"] == 162
    assert norms["flipped_by_n_changes"]["1"] == 1
    assert [s["choices"]["model"] for s in norms["single_flips"]] == ["ols_pooled"]
    assert norms["estimate_min"] < 0 < norms["estimate_max"] < 0.06
    assert changed_steps(2, norms["single_flips"][0]["choices"]) == ["model"]


def test_recorded_religiosity_run_finds_no_flip():
    snapshot = recorded(1)
    report = snapshot.report
    assert snapshot.llm == "scripted" and snapshot.usage.cost_usd == 0
    assert report.minimal_flip is None and snapshot.flip is None
    assert report.robustness == 1.0 and report.n_flipped == 0 and report.n_failed == 0
    assert report.n_universes == 40
    results = [u.result for u in snapshot.garden.universes.values() if u.result]
    assert all(r.ci_low > 0 and r.p_value < 0.05 for r in results)


def test_recorded_norms_run_finds_the_verified_single_flip():
    snapshot = recorded(2)
    flip = snapshot.report.minimal_flip
    assert flip is not None and flip.reproduced is True
    assert [(c.step_id, c.to_option) for c in flip.changes] == [("model", "ols_pooled")]
    assert flip.flipped_result.estimate > 0 and flip.flipped_result.p_value > 0.05
    assert flip.baseline_verdict == "DEPENDS ON NORMS"
    assert 0.5 < snapshot.report.robustness < 1.0 and snapshot.report.n_failed == 0


@pytest.mark.parametrize("rq", [1, 2])
def test_narrator_states_only_numbers_of_the_recorded_run(rq):
    snapshot = recorded(rq)
    fixture = json.loads((CASES_DIR / CASE_IDS[rq] / "fixtures" / "narrator.json").read_text())
    text = fixture["parsed"]["narrative"]
    base = snapshot.report.original_result
    assert f"{base.estimate:.3f}" in text and f"{base.ci_low:.3f}" in text
    assert f"{snapshot.report.n_universes} universes" in text
    assert snapshot.report.original_verdict in text
    done = [u.result for u in snapshot.garden.universes.values() if u.result]
    for value in (min(r.estimate for r in done), max(r.estimate for r in done)):
        assert f"{value:.3f}" in text
    spec = case_spec(rq)
    teams = sorted(r.estimate for r in spec.reference)
    assert f"{teams[0]:.3f}" in text and f"{teams[-1]:.3f}" in text
    allowed = {f"{r.estimate:.3f}" for r in done} | {f"{teams[0]:.3f}", f"{teams[-1]:.3f}"}
    stated = set(re.findall(r"beta = (-?\d\.\d{3})", text))
    assert stated <= allowed
    flip = snapshot.report.minimal_flip
    if flip is not None:
        assert f"p = {flip.flipped_result.p_value:.3f}" in text
