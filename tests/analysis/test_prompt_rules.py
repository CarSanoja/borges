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


def test_planner_leaves_covariate_sets_to_the_adjustment_step() -> None:
    text = " ".join(PLANNER_SYSTEM.split())
    assert "it is the only place covariates are chosen" in text
    assert "no model option names a covariate set of its own" in text
    assert "Never create a separate step that chooses covariates by dropping columns" in (
        PLANNER_SYSTEM
    )


def test_coder_takes_p_values_and_intervals_from_the_fitted_result() -> None:
    assert "from the fitted result (`pvalues`, `conf_int()`" in CODER_SYSTEM
    assert "never recompute them from a hand-written distribution" in CODER_SYSTEM


def test_no_prompt_asks_for_a_multiplication_by_100() -> None:
    assert "multiply the estimate and both interval bounds by 100" not in PLANNER_SYSTEM
    assert "multiply the estimate and both bounds by 100" not in CODER_SYSTEM
    assert "in the units of the estimand" not in CODER_SYSTEM


def test_coder_returns_estimates_on_the_natural_scale() -> None:
    assert "natural scale of the estimator" in CODER_SYSTEM
    assert "Borges converts units itself" in CODER_SYSTEM
    assert "never multiply by 100" in CODER_SYSTEM


def test_coder_forbids_row_selection_by_value_in_a_model_step() -> None:
    assert "A model step never selects rows by value" in CODER_SYSTEM
    assert "The only rows a model may drop are incomplete ones" in CODER_SYSTEM


def test_planner_requires_an_adjustment_step_and_two_model_families_for_associations() -> None:
    text = " ".join(PLANNER_SYSTEM.split())
    assert "regression-style association" in text
    assert "adjustment step and a model step with real alternatives" in text
    assert 'writes the chosen column names to ctx["covariates"] and never drops columns' in text
    assert "at least two options from different model families" in text
    assert "drops one level (drop_first=True)" in text


def test_planner_forbids_options_that_reproduce_the_default() -> None:
    text = " ".join(PLANNER_SYSTEM.split())
    assert "Every option must change the analysis" in text
    assert "reproduces the default on these data" in text


def test_judge_rejects_no_op_alternatives_against_the_conventional_spec() -> None:
    from borges.analysis.prompts.judge import SYSTEM as JUDGE_SYSTEM

    text = " ".join(JUDGE_SYSTEM.split())
    assert "would reproduce the conventional option's result on these data is a no-op" in text
    assert 'accepted=false with reason "equivalent to the conventional option"' in text


def test_planner_forbids_dummy_fixed_effects_for_identifiers_with_many_levels() -> None:
    assert "never dummy fixed effects" in PLANNER_SYSTEM
    assert "Cluster the standard errors on them or aggregate to that unit" in PLANNER_SYSTEM


def test_planner_defaults_to_the_named_profile_and_offers_a_trend_for_dated_exposures() -> None:
    text = " ".join(PLANNER_SYSTEM.split())
    assert "the default covariate set holds every column" in text
    assert "linear time trend" in text and "Month dummies are collinear" in text


def test_judge_keeps_a_pre_exposure_confounder_in_the_same_estimand() -> None:
    from borges.analysis.prompts.judge import SYSTEM as JUDGE_SYSTEM

    text = " ".join(JUDGE_SYSTEM.split())
    assert "plausible pre-exposure confounder" in text
    assert "a mediator, or a consequence of the outcome" in text


def test_judge_reads_cluster_counts_and_accepts_t_for_cluster_assigned_exposures() -> None:
    from borges.analysis.prompts.judge import SYSTEM as JUDGE_SYSTEM

    text = " ".join(JUDGE_SYSTEM.split())
    assert "Read the number of clusters from the distinct values listed under the option" in text
    assert "an exposure assigned to whole clusters" in text
    assert "t critical values on clusters minus one degrees of freedom" in text


def test_ranges_are_written_and_coded_as_ranges_not_two_value_lists() -> None:
    planner = " ".join(PLANNER_SYSTEM.split())
    assert '"from 7 to 14 inclusive"' in planner and "never write either in brackets" in planner
    coder = " ".join(CODER_SYSTEM.split())
    assert "`x.between(7, 14)`" in coder and "`x.isin([7, 14])` keeps only 7 and 14" in coder


def test_a_status_from_an_ordered_answer_keeps_each_group_a_run_of_neighbouring_answers() -> None:
    from borges.analysis.prompts.judge import SYSTEM as JUDGE_SYSTEM

    judge = " ".join(JUDGE_SYSTEM.split())
    assert "each group is a run of neighbouring answers" in judge
    assert "with married women counted as single" in judge and "is rejected" in judge
    planner = " ".join(PLANNER_SYSTEM.split())
    assert "never put an answer between two answers of the other group" in planner


def test_a_cox_model_is_written_with_phreg_and_read_by_its_term_name() -> None:
    coder = " ".join(CODER_SYSTEM.split())
    assert 'smf.phreg("days ~ exposure + age", data, status=data["event"]).fit()' in coder
    assert "fit.model.exog_names.index(name)" in coder and "lifelines is not installed" in coder
    planner = " ".join(PLANNER_SYSTEM.split())
    assert "PHReg for a Cox model of a time to an event" in planner
    assert "R's Surv(), lifelines and parametric survival regressions" in planner
    assert "R's Surv() does not exist in a formula" in coder
