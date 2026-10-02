from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.prompts import messages

SYSTEM = """You are an independent methodologist. Score how defensible one analysis option is \
for this exact question and estimand, on a scale from 0 to 1.

Scale: 0.9-1.0 standard practice any reviewer accepts; 0.6-0.9 a reasonable alternative a \
reviewer would accept with a sentence of justification; 0.3-0.6 questionable, needs strong \
special justification; below 0.3 indefensible, outcome-driven, or it changes the estimand.

When column notes are given, judge the option against what the data are said to contain: an \
option that does not fit the data as described, or whose own rationale concedes it does not \
fit, is indefensible.

An option that is only a linear rescaling of the conventional one (a sum instead of a mean, \
a z-score of the same scale, the first principal component of two standardised items) cannot \
change a standardised estimate: set accepted=false with reason "equivalent to the conventional \
option".

Penalise any option that changes the question or the estimand, leaks the outcome, or looks \
chosen to produce a result. Set accepted=true only when defensibility is at least 0.6. Give a \
one or two sentence reason and, when one exists, a short source for the practice.

Return only JSON matching the requested schema."""


def build_messages(
    plan: AnalysisPlan, step: Step, option: Option, column_notes: str = ""
) -> list[dict[str, str]]:
    notes_block = f"\n{column_notes}" if column_notes else ""
    user = (
        f"Question: {plan.question}\nEstimand: {plan.estimand}\n"
        f"Step: {step.id} ({step.kind}) {step.title}. {step.description}\n"
        f"Conventional option(s) at this step: "
        f"{'; '.join(o.label for o in step.options if o.is_default) or 'none'}\n"
        f"Option under review {option.id}: {option.label}\n"
        f"Rationale: {option.rationale}\nSpec: {option.spec}"
        f"{notes_block}"
    )
    return messages(SYSTEM, user)
