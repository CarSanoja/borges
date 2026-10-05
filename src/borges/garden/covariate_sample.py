"""Covariate options that change the sample, not only the adjustment.

A bank adversary option at 5fb4084, "Adjust for prior contact history: pdays binned, previous,
poutcome", binned pdays with -1 as 'never'. In this data the customers never contacted have no
pdays, so the new column was missing for 82% of the rows and the model dropped them: n fell from
45,211 to 8,252 under an adjustment label. A covariate option whose universes keep less than 80% of
the rows their twins with the step's default keep is reported as a change of sample.

At 1ecb614 the bank covariate option kept every row under the encoding that made missing values a
category and 8,182 under the ordinal encoding: when only some of its universes lose rows, the note
counts them and names the choice they share that the others lack.

At 7885ab7 the bank baseline itself listed pdays among its covariates and fitted 8,252 of the 45,211
rows that reached its model, with no note: when the original analysis fits less than 80% of the
rows its model step receives, the report says so and names the columns it reads that are missing
in that many rows.
"""

from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Garden, Universe

SHARE = 0.8


def _key(choices: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(choices.items()))


def _shared(plan: AnalysisPlan, step_id: str, low: list[Universe], high: list[Universe]) -> str:
    for other in plan.decision_steps:
        if other.id == step_id:
            continue
        chosen = {u.choices.get(other.id) for u in low}
        if len(chosen) == 1 and not chosen & {u.choices.get(other.id) for u in high}:
            option = next((o for o in other.options if o.id in chosen), None)
            if option is not None:
                return f" (those with '{option.label}' at the step '{other.title}')"
    return ""


def _where(plan: AnalysisPlan, step_id: str, pairs: list[tuple[int, int, Universe]]) -> str:
    low = [u for kept, rows, u in pairs if rows < SHARE * kept]
    if len(low) == len(pairs):
        return "its universes keep"
    high = [u for kept, rows, u in pairs if rows >= SHARE * kept]
    return (
        f"in {len(low)} of its {len(pairs)} universes{_shared(plan, step_id, low, high)} it keeps"
    )


def covariate_sample_caveats(plan: AnalysisPlan, garden: Garden) -> list[str]:
    done = garden.finished()
    by_choices = {_key(u.choices): u for u in done}
    notes = []
    for step in plan.decision_steps:
        if step.kind != "feature":
            continue
        default = step.default
        for option in step.options:
            if option.id == default.id:
                continue
            pairs = [
                (twin.result.n, u.result.n, u)
                for u in done
                if u.choices.get(step.id) == option.id and u.result is not None
                if (twin := by_choices.get(_key({**u.choices, step.id: default.id}))) is not None
                and twin.result is not None
            ]
            if not pairs:
                continue
            kept, rows, _ = min(pairs, key=lambda p: p[1] / p[0])
            if rows >= SHARE * kept:
                continue
            notes.append(
                f"The option '{option.label}' of the step '{step.title}' changes the sample, not "
                f"only the adjustment: its covariates are missing in rows the model then drops, so "
                f"{_where(plan, step.id, pairs)} {rows:,} of the {kept:,} rows that "
                f"'{default.label}' keeps, "
                "and its estimates describe that subset."
            )
    return notes


def _read_columns(plan: AnalysisPlan, garden: Garden) -> str:
    baseline = garden.baseline
    return " ".join(
        f"{o.spec} {o.code or ''}"
        for s in plan.steps
        for o in s.options
        if baseline is not None and baseline.choices.get(s.id, s.default.id) == o.id
    )


def baseline_sample_caveats(plan: AnalysisPlan, garden: Garden) -> list[str]:
    baseline = garden.baseline
    if baseline is None or baseline.result is None or not baseline.traces:
        return []
    rows, fitted = baseline.traces[-1].rows_before, baseline.result.n
    if not rows or fitted >= SHARE * rows:
        return []
    text = _read_columns(plan, garden)
    lost = rows - fitted
    missing = [
        c.name
        for c in plan.dataset.columns
        if c.n_missing >= 0.5 * lost and re.search(rf"\b{re.escape(c.name)}\b", text)
    ]
    where = (
        f"the rows where {', '.join(missing)} {'is' if len(missing) == 1 else 'are'} missing"
        if missing
        else "the rows with missing values in its inputs"
    )
    return [
        f"The original analysis fits {fitted:,} of the {rows:,} rows that reach its model: the "
        f"model drops {where}, so the verdict describes that subset, not every row."
    ]
