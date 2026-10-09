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

Another operationalisation of the same construct is an alternative, not a change of the \
estimand: a different window or cut-off the field uses for the construct, another defensible \
coding of a category (which response options count in which group), an exclusion rule for data \
quality or the absence of one, or another set of the published items. Such an option changes \
which rows fall in which group, and that sensitivity is what the analysis studies: score it by \
whether researchers in the field use or would defend it, not by its distance from the \
conventional option shown below, which is only the starting point of this analysis and not \
necessarily the published one. Keep "changes the estimand" for an option that measures another \
construct (the opposite phase as the high window, a group the question does not compare) or \
answers another question.

When the question asks what the exposure does (whether it reduced, caused, improved or worked) or \
compares groups at equal values of other variables (the same risk profile, holding a factor \
constant), adjusting for a variable measured before the exposure that plausibly drives both the \
exposure and the outcome estimates the same effect without that confounding: it is not a change \
of the estimand, even when the conventional option, the step's title or the user's own analysis \
is unadjusted, because an unadjusted comparison of observational data keeps the confounding in \
the estimate. Score it by whether the variable is a plausible pre-exposure confounder. Adjusting \
for a variable the exposure itself changes (a mediator, or a consequence of the outcome) does \
change the estimand.

A rationale may argue from the result it hopes to produce ("may reveal a significant \
difference when the mean gap is not significant", "could yield a significant effect"). That \
hope is not a reason: ignore it and score the method alone; when nothing but the hoped-for result \
supports the option, it is outcome-driven and scores below 0.3. Your reason states the \
methodological ground in your own words and never repeats the hoped-for result.

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
