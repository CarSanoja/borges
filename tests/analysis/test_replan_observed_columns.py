from __future__ import annotations

from borges.analysis.prompts.replan import build_replan_messages, observed_columns
from tests.analysis.fakes import make_plan

KEY_ERROR = (
    "KeyError: 'day' | columns available (3): ['user_id', 'variant', 'converted']; ctx keys: []"
)


def test_the_columns_a_failed_option_saw_are_read_from_its_error() -> None:
    assert observed_columns(["other", KEY_ERROR]) == ["user_id", "variant", "converted"]


def test_a_truncated_column_list_is_not_trusted() -> None:
    truncated = "KeyError: 'x' | columns available (120): ['a', 'b'] ...; ctx keys: []"
    assert observed_columns([truncated]) is None


def test_the_replan_prompt_lists_only_the_columns_seen_on_the_sample() -> None:
    plan = make_plan()
    step = plan.steps[-1]
    user = build_replan_messages(plan, step, [("o1", "with day", "use day", KEY_ERROR)])[-1]
    assert "Columns this step saw on the sample" in user["content"]
    assert "Columns available when this step runs" not in user["content"]
    listed = user["content"].split("Columns this step saw on the sample")[1].split("\n")[0]
    assert "'day'" not in listed and '"day"' not in listed
    assert "user_id" in listed


def test_without_an_observed_list_the_plan_columns_are_used() -> None:
    plan = make_plan()
    user = build_replan_messages(plan, plan.steps[-1], [("o1", "l", "s", "boom")])[-1]
    assert "Columns available when this step runs" in user["content"]


def test_a_model_replan_is_told_which_ctx_keys_and_products_it_must_read() -> None:
    from borges.analysis.models import Option, Step

    def option(oid: str, spec: str) -> Option:
        return Option(id=oid, label=oid, rationale="r", spec=spec, is_default=oid.endswith("0"))

    covariates = Step(
        id="cov",
        title="Covariate set",
        kind="feature",
        description="d",
        options=[option("c0", "ctx['covariates'] = []"), option("c1", "ctx['covariates'] = ['a']")],
    )
    score = Step(
        id="sc",
        title="Score",
        kind="transform",
        description="d",
        produces=["score"],
        options=[option("s0", "mean of items"), option("s1", "first component")],
    )
    model = Step(
        id="m", title="Model", kind="model", description="d", options=[option("m0", "OLS")]
    )
    plan = make_plan().model_copy(update={"steps": [covariates, score, model]})
    user = build_replan_messages(plan, model, [("m0", "l", "s", "boom")])[-1]["content"]
    assert (
        "must read ctx['covariates'], set differently by the earlier step 'Covariate set'" in user
    )
    assert "must use score, built by the earlier step 'Score'" in user
