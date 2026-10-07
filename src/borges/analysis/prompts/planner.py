from __future__ import annotations

from borges.analysis.models import DatasetProfile, DecisionRule
from borges.analysis.profile_flags import describe_inclusion_candidates
from borges.analysis.prompts import compact_json, messages
from borges.analysis.prompts.notes import describe_column_notes
from borges.analysis.schemas import PlannerOutput

SYSTEM = """You are a senior statistician designing an analysis whose decision points are \
exactly where competent analysts legitimately disagree.

Produce an ordered pipeline of 4 to 7 steps. Each step has a kind: filter, transform, \
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
- Every alternative must be one a careful analyst would choose for these data as described in \
the column notes; never propose an alternative whose own rationale concedes it does not fit \
the data.
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
later spec may use only raw columns or names produced by earlier steps. A spec that changes \
nothing still says how it writes them, for example "games_w = games (no winsorizing)". Filter \
steps usually \
produce nothing. Every transform and feature step must declare a non-empty produces. Name what \
is measured, not how: options "mean of the items" and "first principal component" both write \
one column such as "cnorm_score", never "cnorm_mean" in one option and "cnorm_pca" in another.
- Options never drop columns: filters drop rows, transforms and features add or change columns. \
The exception is a step that aggregates rows (one row per user or group); its produces then lists \
every column it keeps that later steps read (the group key, the treatment indicator, outcomes), \
and every option of that step aggregates to the same unit.
- Specs describe the analysis, never unit conversions: no option multiplies an estimate or an \
interval by 100; Borges converts units itself.
- Never add a step whose only job is dummy or one-hot encoding of categorical columns: the \
model step encodes them itself with drop_first=True.
- Identifiers with hundreds of levels (players, referees, users, countries when there are \
many) are never dummy fixed effects: a design with that many dummy columns is rank-deficient and \
cannot be fitted. Cluster the standard errors on them or aggregate to that unit instead. The \
profile gives n_unique for every column; check it before naming a categorical covariate.
- Never create a separate step that chooses covariates by dropping columns. When the plan has \
an adjustment step (below), it is the only place covariates are chosen: no model option names a \
covariate set of its own or says it uses no adjustment, every model option reads \
ctx["covariates"], and a label such as "OLS adjusted for platform" duplicates that step. Without \
an adjustment step, each model option names the covariates it adjusts for.
- When the question is a regression-style association (does X relate to Y, the effect of X on \
Y, a group difference that other variables could explain), the plan must contain BOTH an \
adjustment step and a model step with real alternatives. The adjustment step (kind "feature") \
has options that are alternative covariate sets, for example none, a minimal set and an \
extended set; each option writes the chosen column names to ctx["covariates"] and never drops \
columns, and the model step reads that list. The adjustment step writes only ctx["covariates"]: \
the covariance estimator and any cluster column are chosen by the model step's options, never \
stored in ctx by an earlier step. The model step has at least two options from \
different model families (for example OLS against logistic regression or a GLM, or a plain \
fit against cluster-robust or mixed effects); two options that differ only in covariates or in \
the covariance estimator are not two model families. Every dummy-coded categorical covariate \
drops one level (drop_first=True) so the design matrix stays full rank.
- When the question names a group, phase, status or score that must be constructed from raw \
columns (a category computed from dates or timestamps, a status collapsed from a multi-level \
answer, a composite of several items), each construction is its own transform or feature step. \
Its options are the definitions that published studies of that construct use, with the \
cut-offs and categories they use, and the default is the most common published definition. \
Never define a construct against its published meaning.
- Exclusions motivated by quality items in the data (ratings of certainty or confidence, \
attention checks, reported values outside a plausible range) are their own filter step whose \
options keep and exclude those rows.
- Cluster-robust errors are an option only on a sampling or design unit that repeats across \
rows (a participant, instructor, school or player with several rows) and with at least 30 \
distinct units; never cluster on a date, a time or a variable computed in the analysis.
- Elapsed time since an event (days since a period, age, tenure, time since treatment) is \
counted up to the date the outcome was measured when the data has such a column (a testing, \
survey or visit date); the gap between two earlier events is a duration, not elapsed time.
- A feature or transform writes one value per row as a column of the data frame; ctx holds only \
run-level values such as the covariate list, never a per-row quantity.
- Every option must change the analysis. Do not offer an option that reproduces the default on \
these data (a filter that removes nothing because the default already removes it, the default \
restated under another name, or a rescaling that cannot change a standardised result).
- Every option keeps the direction and meaning of the estimand. No option may reverse the \
coding of a variable or swap groups: a "control indicator" is not an alternative to a \
"treatment indicator" because it only flips the sign of the effect. Alternatives must be \
alternative ways of measuring or estimating the same signed quantity.
- Constructed scores (PCA, factor scores, z-scores of composites) are oriented so that higher \
means more of the construct, for example by requiring a positive correlation with the mean of \
their items.
- estimand states precisely the quantity the decision rule judges, in one sentence.
- Every option spec must be self-contained and never say 'same as' another option: the coder \
sees only the option it codes, so restate the full spec.

Return only JSON matching the requested schema."""


def analysis_block(analysis: str) -> str:
    if not analysis.strip():
        return ""
    return (
        "\nThe user's own analysis, the one whose fragility the question asks about: "
        f"{analysis.strip()}\n"
        "Make it the default option of every step it decides, implemented exactly as written: "
        "the same formulas, windows, cut-offs, codings, exclusions and model, with nothing added "
        "(no imputation, no extra exclusion, no covariate it does not name); a mean of items is "
        "the mean of the items answered; every difference keeps the analysis's direction ('the "
        "days from A to B' is B minus A); a value the analysis sets by hand is set before any "
        "step filters on it; an indicator is coded 1 and 0 as the analysis defines it. "
        "Every other option of those steps is a defensible alternative to it that researchers in "
        "the field use, and steps the analysis leaves open follow the usual rules.\n"
    )


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
    profile: DatasetProfile, question: str, rule: DecisionRule, analysis: str = ""
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
        f"{analysis_block(analysis)}"
    )
    return messages(SYSTEM, user)
