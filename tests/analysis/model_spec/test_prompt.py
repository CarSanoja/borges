from __future__ import annotations

from borges.analysis.model_spec.prompt import SYSTEM, build_spec_messages
from tests.analysis.fakes import make_plan


def test_prompt_carries_the_option_columns_and_scale() -> None:
    plan = make_plan()
    step = plan.step("m1")
    messages = build_spec_messages(plan, step, step.option("welch"))
    user = messages[1]["content"]
    assert messages[0]["content"] == SYSTEM
    assert "Mean difference in outcome between groups" in user
    assert "Label welch" in user and "Spec for welch on outcome" in user
    assert "Columns available when this step runs: group, outcome" in user
    assert "Decision rule" in user
    assert "Estimator" in user


def test_system_names_every_field_and_the_unsupported_cases() -> None:
    for word in ("supported", "family", "outcome", "exposure", "moderator", "covariates_from_ctx"):
        assert word in SYSTEM
    for word in ("offset_log", "cov_type", "standardize", "report", "multilevel", "t-tests"):
        assert word in SYSTEM


def test_earlier_steps_are_listed() -> None:
    plan = make_plan()
    step = plan.step("m1")
    user = build_spec_messages(plan, step, step.option("ols"))[1]["content"]
    assert "Spec for keep on outcome" in user


def test_system_explains_exposure_level_and_marginal_effect() -> None:
    assert "exposure_level" in SYSTEM and '"treatment minus control" means level' in SYSTEM
    assert "marginal_effect" in SYSTEM
