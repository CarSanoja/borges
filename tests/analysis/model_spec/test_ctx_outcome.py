from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from borges.analysis import coder_checks
from borges.analysis.model_spec.ctx_outcome import candidate_specs, ctx_outcome_names, pin_outcome
from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import AnalysisPlan, ColumnProfile, Step
from tests.analysis.fakes import make_option
from tests.analysis.model_spec.test_request import GOOD_SPEC, code_welch, llm_with, plan_with_score

PICK = "def apply(df, ctx):\n    ctx['outcome'] = {name!r}\n    return df"


@pytest.fixture(autouse=True)
def real_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder_checks, "check_code", lambda code, kind, intent="": [])


def plan_choosing_outcome(second: str = "PICK") -> AnalysisPlan:
    plan = plan_with_score()
    plan.dataset.columns.append(
        ColumnProfile(name="outcome2", dtype="float64", n_missing=0, n_unique=90)
    )
    first = make_option("main", True, PICK.format(name="outcome"))
    other = make_option("alt", False, PICK.format(name="outcome2") if second == "PICK" else second)
    choose = Step(id="f1", title="Outcome", kind="feature", description="d", options=[first, other])
    plan.steps.insert(1, choose)
    return plan


def test_the_literal_names_earlier_options_store_are_the_candidates() -> None:
    plan = plan_choosing_outcome()
    available = ["group", "outcome", "score", "outcome2"]
    assert ctx_outcome_names(plan, plan.step("m1"), available) == ["outcome", "outcome2"]
    computed = plan_choosing_outcome("def apply(df, ctx):\n    ctx['outcome'] = pick(df)\n")
    assert ctx_outcome_names(computed, computed.step("m1"), available) is None


def test_an_outcome_chosen_in_a_spec_not_yet_coded_is_a_candidate() -> None:
    plan = plan_choosing_outcome()
    for option, name in zip(plan.steps[1].options, ["outcome", "outcome2"], strict=True):
        option.code = None
        option.spec = f"Use the pre-existing {name} column. Write '{name}' to ctx['outcome']."
    available = ["group", "outcome", "score", "outcome2"]
    assert ctx_outcome_names(plan, plan.step("m1"), available) == ["outcome", "outcome2"]


async def test_a_ctx_outcome_is_templated_and_read_at_run_time() -> None:
    plan = plan_choosing_outcome()
    llm = llm_with(GOOD_SPEC)
    code, attempts, note = await code_welch(llm, plan)
    assert note == "template: ols" and attempts == 1 and code is not None
    assert "ctx['outcome'] (one of: outcome, outcome2)" in llm.calls[0].messages[1]["content"]
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"score": rng.normal(size=200)})
    frame["outcome"] = 2.0 * frame["score"] + rng.normal(size=200)
    frame["outcome2"] = -1.0 * frame["score"] + rng.normal(size=200)
    namespace: dict = {}
    exec(code, namespace)
    first = namespace["estimate"](frame, {"outcome": "outcome"})["estimate"]
    second = namespace["estimate"](frame, {"outcome": "outcome2"})["estimate"]
    assert first == pytest.approx(2.0, abs=0.3) and second == pytest.approx(-1.0, abs=0.3)


def test_a_standardised_outcome_follows_the_candidate() -> None:
    spec = ModelSpecOutput.model_validate(
        {
            "supported": True,
            "family": "ols",
            "outcome": "wb_overall",
            "exposure": "religiosity",
            "standardize": ["wb_overall", "religiosity"],
        }
    )
    names = ["wb_overall", "wb_psych"]
    lists = [c.standardize for c in candidate_specs(spec, names)]
    assert lists == [["wb_overall", "religiosity"], ["wb_psych", "religiosity"]]
    other = spec.model_copy(update={"outcome": "wellbeing", "standardize": ["wellbeing"]})
    pinned = pin_outcome(other, names)
    assert pinned.outcome == "wb_overall" and pinned.standardize == ["wb_overall"]
