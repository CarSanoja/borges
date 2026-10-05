from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Step
from borges.analysis.prompts import compact_json, messages

SYSTEM = """You are a code reviewer for a robustness analysis. Several analysis options were \
written for one step, each from a short spec, and each was executed on a sample of the data. \
For every option decide two things from the code and the observed effects.

1. faithful: does the code do what the spec says, given the observed effects? Example: a \
"keep all rows" filter that dropped half the rows, or every row of one group, is unfaithful. \
So is a filter whose dropped_rows_by shows it removed a group the spec never mentions, or a \
column the spec says is created that is missing or constant. For the model step, the \
estimator the spec names must be the one the code fits (a "Firth" or "Bayesian" option that fits \
a plain Logit, or a "clustered" option without cluster-robust errors, is unfaithful), and \
p_value must be a two-sided p-value for the null of no effect, not a share of bootstrap draws. \
A row filter other than complete cases (rows dropped only for missing values) inside the model \
step's code, such as keeping only rows where a column equals a value, is unfaithful: row \
selection by value belongs to a filter step, and the filter step the model code duplicates \
would become a silent no-op.
Units are converted by Borges after the step: do not flag a result for being a proportion \
rather than percentage points. The code contract overrides a spec on two points: results are \
returned on the natural scale of the estimator (never multiplied by 100) and standard errors, \
intervals and p-values come from the fitted statsmodels result. Code that follows the contract \
where the spec says otherwise is faithful; never ask for a multiplication by 100. The reported \
scale is also set by Borges from the decision rule: exponentiating a log-link coefficient into an \
odds ratio or rate ratio, or reporting an average marginal effect for a difference in \
proportions, is faithful even when the spec mentions a raw coefficient. Equally, code that \
returns the fitted coefficient is faithful when the spec asks to convert it into a rate ratio, a \
percent change, a marginal effect or additional units: Borges does that conversion. Dropping a \
covariate that is an exact linear combination of earlier columns (an aliased column, as R's lm \
does) is faithful too: it leaves the fitted model unchanged. So is dummy coding as pandas does \
it: get_dummies(drop_first=True) drops the first level in sorted order, and the exposure's \
estimate does not depend on which level is the reference, so code that builds the dummies \
get_dummies makes is faithful even when the spec names another reference level or lists a dummy \
of the dropped level. The names listed under "Every option \
must create" override a spec as well: an option whose spec says it changes nothing or adds no \
column is faithful when it writes those names as an unchanged copy of the column they are built \
from, or as 0 for an indicator that none of its rows has.
2. changes_estimand: does the option change the question rather than the analysis? Examples: \
swapping the groups, reversing the coding of a variable, measuring a different outcome. A \
different but legitimate way to measure or clean the same thing does not change the estimand.

Rules: judge every option listed, once, by its option_id, against its own spec only; options \
of the same step are meant to differ from each other. Use the observed effects as evidence, \
not the label. Mark faithful=false only when you can quote the phrase of that option's own spec \
that the code or the effects contradict: copy it word for word into quote (Borges checks that the \
spec contains it). The names under "Every option must create" are shared by the step and may \
describe another option's method, such as log_deaths written by a square-root option: judge the \
computation the spec states, not the column name. When the code and \
effects are consistent with the spec, answer faithful=true, changes_estimand=false and an \
empty problem. When faithful is false, state in the problem, in one or two sentences with the \
column or group names and numbers, what the code does instead of what the spec says, so that \
the coder can fix it.

Return only JSON: {"verdicts": [{"option_id", "faithful", "changes_estimand", "problem", \
"quote"}]}."""


def _column_notes(plan: AnalysisPlan) -> dict[str, str]:
    return {c.name: c.note for c in plan.dataset.columns if c.note}


def build_messages(
    plan: AnalysisPlan, step: Step, entries: list[dict[str, object]]
) -> list[dict[str, str]]:
    notes = _column_notes(plan)
    parts = [
        f"Estimand: {plan.estimand}",
        f"Step: {step.id} ({step.kind}) {step.title}. {step.description}",
    ]
    if step.produces:
        parts.append(f"Every option must create: {', '.join(step.produces)}")
    if notes:
        parts.append(f"Column notes: {compact_json(notes)}")
    parts.append(f"Options: {compact_json(entries)}")
    return messages(SYSTEM, "\n".join(parts))
