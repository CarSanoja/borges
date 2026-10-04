from __future__ import annotations

from borges.analysis.code_guard import check_code
from borges.analysis.code_guard_ctx import ctx_read_violations, varying_ctx_keys
from borges.analysis.code_guard_statsmodels import option_intent
from borges.analysis.code_guard_wide import wide_columns, wide_dummy_violations
from borges.analysis.models import AnalysisPlan, Option, Step


def option_violations(code: str, plan: AnalysisPlan, step: Step, option: Option) -> list[str]:
    intent = option_intent(option)
    found = check_code(code, step.kind, intent)
    if step.kind != "model":
        return found
    return [
        *found,
        *wide_dummy_violations(code, wide_columns(plan.dataset)),
        *ctx_read_violations(code, varying_ctx_keys(plan, step), intent),
    ]
