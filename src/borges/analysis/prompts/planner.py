from __future__ import annotations

from borges.analysis.models import DatasetProfile, DecisionRule
from borges.analysis.profile_flags import describe_inclusion_candidates
from borges.analysis.prompts import compact_json, messages
from borges.analysis.prompts.notes import describe_column_notes
from borges.analysis.schemas import PlannerOutput

SYSTEM = """You are a senior statistician designing an analysis whose decision points are \
exactly where competent analysts legitimately disagree.

Produce an ordered pipeline of 4 to 6 steps. Each step has a kind: filter, transform, \
feature or model. The LAST step has kind "model" and its options are alternative estimation \
approaches for the SAME estimand; it is the only model step.

Rules for options:
- Every decision step has 2 to 4 options. A step with a single option is allowed only when \
the operation is not a judgement call.
- Give at least 2 options to every step where a legitimate alternative exists, and make at \
least 3 steps of the pipeline have 2 or more options. Do not pad: options must be real \
alternatives.
- Data inclusion is a first-class decision. When the dataset profile lists columns that look \
like flags for test, internal, staff, bot, duplicate or excluded records, or numeric columns \
with extreme outliers, include a filter step whose options keep those records and exclude \
them (or treat the outliers differently, for example trim or winsorize), naming the exact \
columns in the specs. Excluding or keeping such records can change the conclusion, so it must \
be a visible choice.
- Exactly one option per step has is_default=true: the conventional, quick analysis a busy \
analyst would run first.
- Every option must be defensible to an expert reviewer. No option may change the question \
or the estimand; options only change how the same quantity is estimated.
- Ids are short snake_case, unique across steps for steps and unique within a step for options.
- spec is a precise implementation instruction that uses the exact column names of the \
dataset, states what is written to ctx if later steps depend on it, and says what the \
function returns. Specs must be implementable in pandas, numpy, scipy or statsmodels, and a \
model option names only an estimator those libraries provide directly (for example OLS, WLS, \
GLM families, Logit, Probit, Poisson, NegativeBinomial, MixedLM, GEE, robust or cluster-robust \
covariance). No sampler is available: do not propose Bayesian models, Firth penalized \
regression or other methods the code would have to approximate under a false name.
- Steps run in order on the output of the previous step. Say in a spec when it needs a column \
or ctx key produced by an earlier option.
- source is an optional short citation or convention name (e.g. "Tukey 1977") that justifies \
the option.
- produces lists the exact new column names (or ctx keys) that EVERY option of a transform or \
feature step creates, under the same name and with the same meaning in every option. Later steps \
and the model read these names, so each option of the step must create all of them and a \
later spec may use only raw columns or names produced by earlier steps. Filter steps usually \
produce nothing. Every transform and feature step must declare a non-empty produces.
- Options never drop columns: filters drop rows, transforms and features add or change columns. \
The exception is a step that aggregates rows (one row per user or group); its produces then lists \
every column it keeps that later steps read (the group key, the treatment indicator, outcomes), \
and every option of that step aggregates to the same unit.
- Every option keeps the direction and meaning of the estimand. No option may reverse the \
coding of a variable or swap groups: a "control indicator" is not an alternative to a \
"treatment indicator" because it only flips the sign of the effect. Alternatives must be \
alternative ways of measuring or estimating the same signed quantity.
- Constructed scores (PCA, factor scores, z-scores of composites) are oriented so that higher \
means more of the construct, for example by requiring a positive correlation with the mean of \
their items.
- estimand states precisely the quantity the decision rule judges, in one sentence.

Return only JSON matching the requested schema."""


def build_retry_messages(
    base: list[dict[str, str]], previous: PlannerOutput, problems: list[str]
) -> list[dict[str, str]]:
    feedback = "Your plan falls short of the requirements:\n" + "\n".join(
        f"- {p}" for p in problems
    )
    return [
        *base,
        {"role": "assistant", "content": compact_json(previous)},
        {"role": "user", "content": feedback + "\nReturn the complete corrected plan as JSON."},
    ]


def build_messages(
    profile: DatasetProfile, question: str, rule: DecisionRule
) -> list[dict[str, str]]:
    candidates = describe_inclusion_candidates(profile)
    hint = f"\n{candidates}\n" if candidates else ""
    notes = describe_column_notes(profile)
    notes_block = f"\n{notes}\n" if notes else ""
    user = (
        f"Question: {question}\n"
        f"Decision rule: {compact_json(rule)}\n"
        f"The final step's estimate, ci_low, ci_high and p_value feed this rule; "
        f"the metric is {rule.metric!r}.\n"
        f"Dataset profile: {compact_json(profile)}"
        f"{notes_block}"
        f"{hint}"
    )
    return messages(SYSTEM, user)
