from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.analysis.prompts import compact_json, messages
from borges.garden.models import Report

SYSTEM = """You write the plain-language summary of a robustness analysis for a decision maker.

Write 150 to 260 words of markdown. Besides the report you receive the whole garden: every \
universe with the decisions it changed and its result, the judge's verdict on every proposed \
option, and the caveats. Let the summary reflect the whole garden, not only the minimal flip: \
say which decisions move the estimate, how the results of the universes spread, and what the \
judge accepted or rejected when that matters. Cover, in this order: the original verdict and its \
estimate; the minimal flip (the fewest defensible changes that reverse the verdict) and why \
each change is defensible, or say clearly that no flip was found; when a flip was found, \
whether it was reproduced by an independent re-execution; and the share of explored universes \
that agree with the original verdict (robustness). When no flip was found there is nothing to \
re-execute: do not mention re-execution or reproducibility, in the summary or in the caveats.

Do not overclaim causality: the influence figures describe how sensitive the analysis is to \
analyst choices, not effects in the world. Say what each change does, and never explain why the \
estimate moved with a statistical mechanism (overdispersion, confounding, outliers, leverage) \
unless the garden has a universe that changes only that and shows it. Use only numbers present in the report. No \
headings, no preamble. Also return 0 to 4 short caveats.

Return only JSON matching the requested schema."""


def build_messages(
    plan: AnalysisPlan,
    report: Report,
    flip_sentence: str | None = None,
    problems: list[str] | None = None,
    garden: dict[str, object] | None = None,
) -> list[dict[str, str]]:
    body = report.model_dump(mode="json", exclude={"narrative", "caveats", "narrator_input_tokens"})
    user = (
        f"Estimand: {plan.estimand}\n"
        f"Decision rule: {compact_json(plan.decision_rule)}\n"
        f"Report: {compact_json(body)}"
    )
    if garden is not None:
        user += f"\nGarden: {compact_json(garden)}"
    if flip_sentence is not None:
        user += (
            f"\nInclude this sentence verbatim in the summary, as its second sentence: "
            f"{flip_sentence}\nName no other option of that step as part of the flip."
        )
    if problems:
        user += "\nYour previous summary was rejected: " + "; ".join(problems) + "."
    return messages(SYSTEM, user)
