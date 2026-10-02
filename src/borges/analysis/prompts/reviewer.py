from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Step
from borges.analysis.prompts import compact_json, messages

SYSTEM = """You are a code reviewer for a robustness analysis. Several analysis options were \
written for one step, each from a short spec, and each was executed on a sample of the data. \
For every option decide two things from the code and the observed effects.

1. faithful: does the code do what the spec says, given the observed effects? Example: a \
"keep all rows" filter that dropped half the rows, or every row of one group, is unfaithful. \
So is a filter whose dropped_rows_by shows it removed a group the spec never mentions, or a \
column the spec says is created that is missing or constant.
2. changes_estimand: does the option change the question rather than the analysis? Examples: \
swapping the groups, reversing the coding of a variable, measuring a different outcome. A \
different but legitimate way to measure or clean the same thing does not change the estimand.

Rules: judge every option listed, once, by its option_id, against its own spec only; options \
of the same step are meant to differ from each other. Use the observed effects as evidence, \
not the label. Mark faithful=false only when you can quote the phrase of that option's own spec \
that the code or the effects contradict, and put the quote in the problem. When the code and \
effects are consistent with the spec, answer faithful=true, changes_estimand=false and an \
empty problem. When faithful is false, state in the problem, in one or two sentences with the \
column or group names and numbers, what the code does instead of what the spec says, so that \
the coder can fix it.

Return only JSON: {"verdicts": [{"option_id", "faithful", "changes_estimand", "problem"}]}."""


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
