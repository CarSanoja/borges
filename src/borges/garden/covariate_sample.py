"""Covariate options that change the sample, not only the adjustment.

A bank adversary option at 5fb4084, "Adjust for prior contact history: pdays binned, previous,
poutcome", binned pdays with -1 as 'never'. In this data the customers never contacted have no
pdays, so the new column was missing for 82% of the rows and the model dropped them: n fell from
45,211 to 8,252 under an adjustment label. A covariate option whose universes keep less than 80% of
the rows their twins with the step's default keep is reported as a change of sample.
"""

from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Garden

SHARE = 0.8


def _key(choices: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(choices.items()))


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
                (twin.result.n, u.result.n)
                for u in done
                if u.choices.get(step.id) == option.id and u.result is not None
                if (twin := by_choices.get(_key({**u.choices, step.id: default.id}))) is not None
                and twin.result is not None
            ]
            if not pairs:
                continue
            kept, rows = min(pairs, key=lambda p: p[1] / p[0])
            if rows >= SHARE * kept:
                continue
            notes.append(
                f"The option '{option.label}' of the step '{step.title}' changes the sample, not "
                f"only the adjustment: its covariates are missing in rows the model then drops, so "
                f"its universes keep {rows:,} of the {kept:,} rows that '{default.label}' keeps, "
                "and its estimates describe that subset."
            )
    return notes
