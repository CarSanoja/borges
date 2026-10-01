from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.analysis.prompts import compact_json, messages
from borges.garden.models import Report

SYSTEM = """You write the plain-language summary of a robustness analysis for a decision maker.

Write 120 to 220 words of markdown. Cover, in this order: the original verdict and its \
estimate; the minimal flip (the fewest defensible changes that reverse the verdict) and why \
each change is defensible, or say clearly that no flip was found; whether the flip was \
reproduced by an independent re-execution; and the share of explored universes that agree \
with the original verdict (robustness).

Do not overclaim causality: the influence figures describe how sensitive the analysis is to \
analyst choices, not effects in the world. Use only numbers present in the report. No \
headings, no preamble. Also return 0 to 4 short caveats.

Return only JSON matching the requested schema."""


def build_messages(plan: AnalysisPlan, report: Report) -> list[dict[str, str]]:
    body = report.model_dump(mode="json", exclude={"narrative", "caveats"})
    user = (
        f"Estimand: {plan.estimand}\n"
        f"Decision rule: {compact_json(plan.decision_rule)}\n"
        f"Report: {compact_json(body)}"
    )
    return messages(SYSTEM, user)
