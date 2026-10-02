from __future__ import annotations

from borges.analysis.models import AnalysisPlan, ColumnProfile, DatasetProfile, DecisionRule, Step
from borges.analysis.prompts.adversary import SYSTEM as ADVERSARY_SYSTEM
from borges.analysis.prompts.adversary import build_messages as adversary_messages
from borges.analysis.prompts.coder import SYSTEM as CODER_SYSTEM
from borges.analysis.prompts.coder import build_messages as coder_messages
from borges.analysis.prompts.planner import SYSTEM as PLANNER_SYSTEM
from borges.analysis.prompts.planner import build_messages as planner_messages
from borges.garden.models import Universe
from tests.analysis.fakes import make_option


def _profile() -> DatasetProfile:
    return DatasetProfile(
        name="t",
        n_rows=10,
        columns=[
            ColumnProfile(
                name="games",
                dtype="int32",
                n_missing=0,
                n_unique=5,
                note="games the player and this referee shared, not the career total",
            ),
            ColumnProfile(name="y", dtype="float64", n_missing=0, n_unique=2),
        ],
    )


def _plan() -> AnalysisPlan:
    return AnalysisPlan(
        question="Q?",
        estimand="E",
        decision_rule=DecisionRule(metric="m"),
        dataset=_profile(),
        steps=[
            Step(
                id="f1",
                title="Filter",
                kind="filter",
                description="d",
                options=[make_option("a", True), make_option("b")],
            ),
            Step(
                id="score",
                title="Score",
                kind="feature",
                description="d",
                options=[make_option("mean", True), make_option("pca")],
                produces=["religiosity"],
            ),
            Step(
                id="m1",
                title="Model",
                kind="model",
                description="d",
                options=[make_option("ols", True), make_option("glm")],
            ),
        ],
    )


def _user(messages: list[dict[str, str]]) -> str:
    return messages[1]["content"]


def test_coder_lists_raw_and_earlier_produced_columns() -> None:
    plan = _plan()
    model = plan.steps[2]
    text = _user(coder_messages(plan, model, model.options[0], None))
    assert "Columns available when this step runs: games, y, religiosity" in text
    assert "Read only the columns available" in text


def test_coder_does_not_list_columns_of_the_current_or_later_steps() -> None:
    plan = _plan()
    score = plan.steps[1]
    text = _user(coder_messages(plan, score, score.options[0], None))
    assert "Columns available when this step runs: games, y\n" in text


def test_coder_states_what_the_step_must_create() -> None:
    plan = _plan()
    score = plan.steps[1]
    text = _user(coder_messages(plan, score, score.options[1], None))
    assert "This step must create: religiosity, with exactly these names for every option" in text


def test_coder_filter_step_has_no_create_line() -> None:
    plan = _plan()
    text = _user(coder_messages(plan, plan.steps[0], plan.steps[0].options[0], None))
    assert "This step must create" not in text


def test_coder_rules_cover_columns_direction_and_orientation() -> None:
    assert "Never drop columns" in CODER_SYSTEM
    assert "filters only drop rows" in CODER_SYSTEM
    assert "correlates positively with the mean of its items" in CODER_SYSTEM
    assert "multiply it by -1" in CODER_SYSTEM
    assert "Never swap" in CODER_SYSTEM
    assert "statsmodels" in CODER_SYSTEM


def test_column_notes_reach_coder_planner_and_adversary() -> None:
    plan = _plan()
    note = "not the career total"
    step = plan.steps[2]
    assert note in _user(coder_messages(plan, step, step.options[0], None))
    assert note in _user(planner_messages(_profile(), "Q?", DecisionRule(metric="m")))
    baseline = Universe(id="u_0", choices={}, kind="baseline")
    assert note in _user(adversary_messages(plan, baseline, 3))


def test_no_notes_block_without_notes() -> None:
    profile = DatasetProfile(
        name="t",
        n_rows=1,
        columns=[ColumnProfile(name="a", dtype="int64", n_missing=0, n_unique=1)],
    )
    assert "Column notes" not in _user(planner_messages(profile, "Q?", DecisionRule(metric="m")))


def test_planner_rules_require_produces_and_forbid_reversals() -> None:
    assert "produces" in PLANNER_SYSTEM
    assert "Options never drop columns" in PLANNER_SYSTEM
    assert "control indicator" in PLANNER_SYSTEM
    assert "higher means more of the construct" in PLANNER_SYSTEM


def test_adversary_rules_forbid_reversals_and_point_to_notes() -> None:
    assert "never reverse the coding" in ADVERSARY_SYSTEM
    assert "column notes" in ADVERSARY_SYSTEM
