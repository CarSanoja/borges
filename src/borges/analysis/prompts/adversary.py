from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.analysis.prompts import compact_json, messages
from borges.analysis.prompts.notes import describe_column_notes
from borges.garden.models import Universe

SYSTEM = """You are a rigorous adversarial reviewer of a data analysis. Your job is to find \
analysis choices that are fully defensible to an expert yet plausibly move the result toward \
the OPPOSITE verdict of the baseline.

Rules:
- Propose NEW options only, attached to existing step ids. Do not repeat an existing option \
or restate its spec.
- Each option must be defensible to a methodologist and must not change the question or the \
estimand. No data dredging, no outcome-driven exclusions without an a-priori rationale.
- Every proposal keeps the direction and meaning of the estimand: never reverse the coding of \
a variable, swap groups or flip a sign, because that changes the sign of the result without \
changing the evidence.
- Read the meaning of each column from the column notes before using it in a proposal or an \
exclusion rule; a column that counts something per row (for example games in a player-referee \
dyad) is not a per-entity total.
- Use the baseline step traces (rows before and after each step on the real data) to target \
steps where the data actually responds to the choice.
- spec must be a precise implementation instruction with exact column names, compatible with \
the options of other steps.
- Ids are short snake_case and unique within the step. source is an optional short citation.
- Prefer a few strong proposals over many weak ones.

Return only JSON matching the requested schema."""


def build_messages(
    plan: AnalysisPlan, baseline: Universe, max_proposals: int
) -> list[dict[str, str]]:
    steps = [
        {
            "id": s.id,
            "kind": s.kind,
            "title": s.title,
            "options": [{"id": o.id, "label": o.label, "spec": o.spec} for o in s.options],
        }
        for s in plan.steps
    ]
    traces = [t.model_dump(mode="json") for t in baseline.traces]
    result = baseline.result.model_dump(mode="json") if baseline.result else None
    notes = describe_column_notes(plan.dataset)
    notes_block = f"{notes}\n" if notes else ""
    user = (
        f"{notes_block}Question: {plan.question}\nEstimand: {plan.estimand}\n"
        f"Decision rule: {compact_json(plan.decision_rule)}\n"
        f"Plan: {compact_json(steps)}\n"
        f"Baseline choices: {compact_json(baseline.choices)}\n"
        f"Baseline result: {compact_json(result)}\n"
        f"Baseline verdict: {baseline.verdict}\n"
        f"Baseline step traces: {compact_json(traces)}\n"
        f"Return at most {max_proposals} proposals."
    )
    return messages(SYSTEM, user)
