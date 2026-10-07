from __future__ import annotations

import ast

from borges.analysis.code_guard import check_code
from borges.analysis.code_guard_coefficient import positional_estimate_violations
from borges.analysis.code_guard_complete import complete_case_violations
from borges.analysis.code_guard_ctx import ctx_read_violations, varying_ctx_keys
from borges.analysis.code_guard_ctx_names import ctx_name_violations
from borges.analysis.code_guard_ctx_promise import read_promise_violations
from borges.analysis.code_guard_ctx_spec import (
    positional_dummy_violations,
    sibling_outcome_violations,
    spec_ctx_write_violations,
)
from borges.analysis.code_guard_ctx_unset import unset_ctx_violations
from borges.analysis.code_guard_ctx_value import ctx_value_violations
from borges.analysis.code_guard_dead_write import dead_write_violations
from borges.analysis.code_guard_interval import interval_level_violations
from borges.analysis.code_guard_missing import missing_violations
from borges.analysis.code_guard_mode import empty_mode_violations
from borges.analysis.code_guard_named_rows import named_rows_only_violations
from borges.analysis.code_guard_produces import products_read_violations, unused_products
from borges.analysis.code_guard_row_filter import row_filter_violations
from borges.analysis.code_guard_row_scale import row_scale_violations
from borges.analysis.code_guard_statsmodels import option_intent
from borges.analysis.code_guard_wide import wide_columns, wide_dummy_violations
from borges.analysis.covariate_ids import covariate_id_violations
from borges.analysis.models import AnalysisPlan, Option, Step


def _mode_violations(code: str) -> list[str]:
    try:
        return empty_mode_violations(ast.parse(code))
    except SyntaxError:
        return []


def option_violations(code: str, plan: AnalysisPlan, step: Step, option: Option) -> list[str]:
    intent = option_intent(option)
    found = check_code(code, step.kind, intent)
    if step.kind != "model":
        return [
            *found,
            *missing_violations(code, intent),
            *_mode_violations(code),
            *ctx_name_violations(code, step, option),
            *spec_ctx_write_violations(code, option.spec),
            *read_promise_violations(code, plan, step, option),
            *ctx_value_violations(code, plan, step),
            *unset_ctx_violations(code, plan, step),
            *sibling_outcome_violations(code, step, option),
            *positional_dummy_violations(code),
            *row_scale_violations(code),
            *row_filter_violations(code, option.spec),
            *covariate_id_violations(code, plan.dataset),
            *dead_write_violations(code),
            *named_rows_only_violations(code, plan, step),
        ]
    return [
        *found,
        *wide_dummy_violations(code, wide_columns(plan.dataset)),
        *complete_case_violations(code, plan.dataset),
        *ctx_read_violations(code, varying_ctx_keys(plan, step), intent),
        *ctx_value_violations(code, plan, step),
        *unset_ctx_violations(code, plan, step),
        *products_read_violations(code, unused_products(plan, step)),
        *interval_level_violations(code),
        *positional_estimate_violations(code),
    ]
