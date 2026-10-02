from __future__ import annotations

import json

import numpy as np
import pytest

from borges.cases.registry import CaseRegistry
from tests.cases.marp_support import CASE_IDS, CASES_DIR, case_frame, case_spec


def test_dataset_is_the_real_marp_release():
    frame = case_frame(1)
    assert len(frame) == 10535
    assert frame["country"].nunique() == 24
    assert int((frame["attention_check"] == 1).sum()) == 10195
    items = [c for c in frame.columns if c.startswith("wb_") and not c.endswith("mean")]
    assert len(items) == 18
    mean = frame[items].mean(axis=1, skipna=True)
    assert np.allclose(mean, frame["wb_overall_mean"], atol=1e-3, equal_nan=True)
    religiosity = frame[[f"rel_{i}" for i in range(1, 10)]]
    assert religiosity.min().min() >= 0 and religiosity.max().max() <= 1


def test_both_cases_ship_the_same_data():
    first = (CASES_DIR / CASE_IDS[1] / "data.parquet").read_bytes()
    second = (CASES_DIR / CASE_IDS[2] / "data.parquet").read_bytes()
    assert first == second


@pytest.mark.parametrize("rq", [1, 2])
def test_registry_lists_the_case_with_its_recording(rq):
    card = CaseRegistry(CASES_DIR).card(CASE_IDS[rq])
    assert card.n_rows == 10535 and card.has_recording


def test_reference_lane_is_the_published_team_results():
    first, second = case_spec(1), case_spec(2)
    assert len(first.reference) == 110 and len(second.reference) == 105
    assert sum(1 for r in first.reference if r.significant) == 110
    assert sum(1 for r in second.reference if r.significant) == 68
    medians = [float(np.median([r.estimate for r in s.reference])) for s in (first, second)]
    assert medians == [pytest.approx(0.12, abs=0.005), pytest.approx(0.039, abs=0.005)]
    assert min(r.estimate for r in second.reference) < 0
    assert "Hoogeveen, Sarafoglou et al., 2022" in first.reference_label


@pytest.mark.parametrize("rq", [1, 2])
def test_readme_states_source_license_and_attribution(rq):
    text = " ".join((CASES_DIR / CASE_IDS[rq] / "README.md").read_text().split())
    for needle in ("CC-By Attribution 4.0", "10.1080/2153599X.2022.2070255", "osf.io/qbdce"):
        assert needle in text
    assert "seeded from the choices the teams published" in text


@pytest.mark.parametrize("rq", [1, 2])
def test_plan_options_carry_team_counts_and_the_adversary_proposes_nothing(rq):
    fixtures = CASES_DIR / CASE_IDS[rq] / "fixtures"
    planner = json.loads((fixtures / "planner.json").read_text())["parsed"]
    assert "seeded from the analytic choices" in planner["estimand"]
    for step in planner["steps"]:
        for option in step["options"]:
            assert "Hoogeveen, Sarafoglou et al. (2022)" in option["source"]
    assert json.loads((fixtures / "adversary.json").read_text())["parsed"] == {"proposals": []}
    alternatives = {
        f"judge__planner__{step['id']}.{option['id']}.json"
        for step in planner["steps"]
        for option in step["options"]
        if not option["is_default"]
    }
    assert {p.name for p in fixtures.glob("judge__*.json")} == alternatives


@pytest.mark.parametrize("rq", [1, 2])
def test_fixtures_claim_no_model_and_no_usage(rq):
    for path in (CASES_DIR / CASE_IDS[rq] / "fixtures").glob("*.json"):
        payload = json.loads(path.read_text())
        assert payload["model"] == "scripted-fixture"
        assert payload["tokens_in"] == 0 and payload["tokens_out"] == 0
