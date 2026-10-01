from __future__ import annotations

from borges.analysis.models import DatasetProfile, DecisionRule
from borges.analysis.prompts import compact_json, messages

SYSTEM = """You are a senior statistician designing an analysis whose decision points are \
exactly where competent analysts legitimately disagree.

Produce an ordered pipeline of 4 to 6 steps. Each step has a kind: filter, transform, \
feature or model. The LAST step has kind "model" and its options are alternative estimation \
approaches for the SAME estimand; it is the only model step.

Rules for options:
- Every decision step has 2 to 4 options. A step with a single option is allowed only when \
the operation is not a judgement call.
- Exactly one option per step has is_default=true: the conventional, quick analysis a busy \
analyst would run first.
- Every option must be defensible to an expert reviewer. No option may change the question \
or the estimand; options only change how the same quantity is estimated.
- Ids are short snake_case, unique across steps for steps and unique within a step for options.
- spec is a precise implementation instruction that uses the exact column names of the \
dataset, states what is written to ctx if later steps depend on it, and says what the \
function returns. Specs must be implementable in pandas, numpy, scipy or statsmodels.
- Steps run in order on the output of the previous step. Say in a spec when it needs a column \
or ctx key produced by an earlier option.
- source is an optional short citation or convention name (e.g. "Tukey 1977") that justifies \
the option.
- estimand states precisely the quantity the decision rule judges, in one sentence.

Return only JSON matching the requested schema."""


def build_messages(
    profile: DatasetProfile, question: str, rule: DecisionRule
) -> list[dict[str, str]]:
    user = (
        f"Question: {question}\n"
        f"Decision rule: {compact_json(rule)}\n"
        f"The final step's estimate, ci_low, ci_high and p_value feed this rule; "
        f"the metric is {rule.metric!r}.\n"
        f"Dataset profile: {compact_json(profile)}"
    )
    return messages(SYSTEM, user)
