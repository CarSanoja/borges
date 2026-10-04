from __future__ import annotations

import ast

from borges.analysis.code_guard import check_code
from borges.analysis.code_guard_ctx import ctx_read_violations, varying_ctx_keys
from borges.analysis.code_guard_ctx_names import ctx_name_violations
from borges.analysis.code_guard_missing import missing_violations
from borges.analysis.code_guard_mode import empty_mode_violations
from borges.analysis.code_guard_produces import products_read_violations, unused_products
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
            *covariate_id_violations(code, plan.dataset),
        ]
    return [
        *found,
        *wide_dummy_violations(code, wide_columns(plan.dataset)),
        *ctx_read_violations(code, varying_ctx_keys(plan, step), intent),
        *products_read_violations(code, unused_products(plan, step)),
    ]
