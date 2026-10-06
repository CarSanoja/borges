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

An option that would reproduce the conventional option's result on these data is a no-op, \
not an alternative: a filter that removes the rows the conventional filter already removes, \
the conventional estimator restated under another name or with a cosmetic change, a covariate \
set identical to the conventional one. Compare the option with the conventional spec shown \
below; when it adds nothing, set accepted=false with reason "equivalent to the conventional \
option".

An option that reverses a variable's direction (orients a score so that higher values mean \
less of what its items measure, flips a sign, swaps the groups) only flips the sign of the \
result: set accepted=false with reason "reverses a variable's direction". Reverse-coding \
negatively worded items so that all items point the same way is not a reversal.

When the option under review is itself the conventional option of its step, judge whether it \
is a correct and standard way to carry out that step for this question: a construct defined \
against its published definition (observations assigned to the wrong category, a window or \
cut-off the field does not use for it) is indefensible even as the conventional choice.

Cluster-robust standard errors are defensible only on a sampling or design unit that repeats \
across rows (participants measured repeatedly, instructors with several courses, schools, \
players) and with at least 30 distinct clusters. Clustering on a date, a time, a variable \
computed in the analysis, or fewer than 30 groups is indefensible: with few clusters the \
interval is too narrow.

Penalise any option that changes the question or the estimand, leaks the outcome, or looks \
chosen to produce a result. Set accepted=true only when defensibility is at least 0.6. Give a \
one or two sentence reason and, when one exists, a short source for the practice.

Return only JSON matching the requested schema."""


def _under_review(option: Option) -> str:
    if option.is_default:
        return "Option under review (it is the conventional option of this step)"
    return "Option under review"


def build_messages(
    plan: AnalysisPlan, step: Step, option: Option, column_notes: str = ""
) -> list[dict[str, str]]:
    notes_block = f"\n{column_notes}" if column_notes else ""
    user = (
        f"Question: {plan.question}\nEstimand: {plan.estimand}\n"
        f"Step: {step.id} ({step.kind}) {step.title}. {step.description}\n"
        f"Conventional option(s) at this step: "
        f"{'; '.join(o.label for o in step.options if o.is_default) or 'none'}\n"
        f"Conventional spec: "
        f"{'; '.join(o.spec for o in step.options if o.is_default) or 'none'}\n"
        f"{_under_review(option)} {option.id}: {option.label}\n"
        f"Rationale: {option.rationale}\nSpec: {option.spec}"
        f"{notes_block}"
    )
    return messages(SYSTEM, user)
