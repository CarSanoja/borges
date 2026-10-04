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
