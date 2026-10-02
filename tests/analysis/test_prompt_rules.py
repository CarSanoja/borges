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
    assert "by its correlation with the plain mean of its items" in CODER_SYSTEM
    assert "score = -score" in CODER_SYSTEM
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


def test_aggregation_is_the_only_exception_to_keeping_columns() -> None:
    assert "aggregates rows" in CODER_SYSTEM
    assert "aggregates rows" in PLANNER_SYSTEM


def test_model_step_starts_from_complete_cases() -> None:
    assert "dropna(subset=" in CODER_SYSTEM
    assert "cluster groups must have the same length" in CODER_SYSTEM


def test_planner_names_only_estimators_the_libraries_provide() -> None:
    assert "do not propose Bayesian models, Firth penalized" in PLANNER_SYSTEM


def test_reviewer_checks_the_named_estimator_and_the_p_value() -> None:
    from borges.analysis.prompts.reviewer import SYSTEM

    assert "estimator the spec names must be the one the code fits" in SYSTEM
    assert "not a share of bootstrap draws" in SYSTEM


def test_narrator_does_not_invent_a_missing_re_execution() -> None:
    from borges.analysis.prompts.narrator import SYSTEM

    assert "When no flip was found there is nothing to re-execute" in SYSTEM


def test_constructed_scores_are_oriented_by_correlation_with_their_items() -> None:
    assert "np.corrcoef(score, items.mean(axis=1))" in CODER_SYSTEM
    assert "Never orient by the sign" in CODER_SYSTEM
    assert "dtype=float" in CODER_SYSTEM


def test_produced_names_say_what_is_measured_not_how() -> None:
    assert "Name what is measured, not how" in PLANNER_SYSTEM.replace("\n", " ")


def test_planner_requires_alternatives_that_fit_the_data_as_described() -> None:
    assert "never propose an alternative whose own rationale concedes it does not fit" in " ".join(
        PLANNER_SYSTEM.split()
    )


def test_planner_makes_covariate_sets_options_of_the_model_step() -> None:
    assert "Covariate sets are options of the model step" in PLANNER_SYSTEM
    assert "Never create a separate step that chooses covariates by dropping columns" in (
        PLANNER_SYSTEM
    )


def test_coder_takes_p_values_and_intervals_from_the_fitted_result() -> None:
    assert "from the fitted result (`pvalues`, `conf_int()`" in CODER_SYSTEM
    assert "never recompute them from a hand-written distribution" in CODER_SYSTEM
