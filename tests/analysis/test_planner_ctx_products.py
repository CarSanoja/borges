from __future__ import annotations

from borges.analysis.planner_ctx_products import ctx_row_shortfall, with_ctx_products
from borges.analysis.planner_validation import plan_shortfalls
from borges.analysis.schemas import PlannedOption, PlannedStep, PlannerOutput
from tests.analysis.fakes import make_profile


def option(option_id: str, spec: str, default: bool = False) -> PlannedOption:
    return PlannedOption(
        id=option_id, label=option_id, rationale="r", spec=spec, is_default=default
    )


def step(kind: str, specs: list[str], produces: list[str] | None = None) -> PlannedStep:
    return PlannedStep(
        id=f"{kind}_step",
        title=kind,
        kind=kind,
        description="d",
        options=[option(f"o{i}", s, i == 0) for i, s in enumerate(specs)],
        produces=produces or [],
    )


COVARIATES = [
    "Write an empty list to ctx['covariates'].",
    "Write ['gender', 'minority'] to ctx['covariates'].",
    'Write ["gender", "age"] to ctx["covariates"].',
]


def produced(*steps: PlannedStep) -> list[list[str]]:
    out = with_ctx_products(PlannerOutput(estimand="e", steps=list(steps)))
    return [s.produces for s in out.steps]


def test_a_ctx_key_every_option_writes_is_what_the_step_produces() -> None:
    assert produced(step("feature", COVARIATES)) == [["covariates"]]


def test_a_key_only_some_options_write_is_not_declared() -> None:
    specs = [COVARIATES[1], "Return the data frame unchanged."]
    assert produced(step("feature", specs)) == [[]]


def test_declared_products_and_non_producing_steps_are_left_alone() -> None:
    model = step("model", ["Fit OLS with ctx['covariates'].", "Fit WLS with ctx['covariates']."])
    declared = step("transform", COVARIATES, produces=["outcome_t"])
    assert produced(model, declared) == [[], ["outcome_t"]]


def test_the_inferred_key_clears_the_missing_produces_shortfall() -> None:
    out = with_ctx_products(PlannerOutput(estimand="e", steps=[step("feature", COVARIATES)]))
    assert not any(
        "do not declare produces" in p for p in plan_shortfalls(out.steps, make_profile())
    )


def test_a_per_row_array_stored_in_ctx_is_a_shortfall() -> None:
    rows = "Create ctx['commitment'] = np.where(df['Relationship'] >= 2, 'committed', 'single')"
    found = ctx_row_shortfall([step("filter", [rows, rows.replace(">= 2", "== 4")])])
    assert found is not None and "filter_step.o0 (ctx['commitment'])" in found
    assert "column of df" in found


def test_run_level_ctx_values_are_not_a_shortfall() -> None:
    assert ctx_row_shortfall([step("feature", COVARIATES)]) is None
    assert ctx_row_shortfall([step("feature", ["ctx['groups'] = ('committed', 'single')"])]) is None


def test_a_per_row_quantity_stored_in_ctx_in_prose_is_a_shortfall() -> None:
    spec = (
        "Compute cycle_length = (StartDateofLastPeriod - StartDateofPeriodBeforeLast).dt.days; "
        "cycle_day = 28 - days_to_next_onset; keep rows where 7 <= cycle_day <= 14; store "
        "cycle_day in ctx['cycle_day'] for possible diagnostics; return filtered DataFrame."
    )
    found = ctx_row_shortfall([step("filter", [spec, spec.replace("14", "12")])])
    assert found is not None and "filter_step.o0 (ctx['cycle_day'])" in found
    assert "computed by a feature step placed before the filter" in found


def test_a_column_name_written_to_ctx_is_not_a_shortfall() -> None:
    named = [
        "Compute religiosity_z = (raw - raw.mean()) / raw.std(); Write religiosity_z to "
        "ctx['religiosity']. Return the DataFrame with added column religiosity_z.",
        "Compute relig = mean of Rel1, Rel2, Rel3. Write relig to ctx['religiosity'] and return "
        "the dataframe with new column 'relig'.",
        "high = 1 if 7 <= day <= 14 else 0; write high to ctx['high_col'] as 'high'.",
    ]
    assert ctx_row_shortfall([step("feature", named)]) is None
