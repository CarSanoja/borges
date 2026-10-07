"""Which universes could not run, where and why, stated from the garden.

A red_cards summary at 508fe2e put three failed universes down to singular-matrix errors; one of
them was a process stopped with exit code -1, and all three used the adversary's referee-country
covariates. The caveat names the failing option, the error and the choice the failures share.
"""

from __future__ import annotations

from collections import Counter

from borges.analysis.models import AnalysisPlan
from borges.garden.degenerate import DEGENERATE_REASON
from borges.garden.models import Garden, Universe
from borges.garden.plausibility import IMPLAUSIBLE_REASON
from borges.garden.reversal import REVERSED_REASON

MAX_GROUPS = 4
MAX_REASON = 120


def could_not_run(garden: Garden) -> list[Universe]:
    return [
        u
        for u in garden.universes.values()
        if u.status == "failed"
        and u.kind != "verification"
        and not (u.error or "").startswith((IMPLAUSIBLE_REASON, REVERSED_REASON, DEGENERATE_REASON))
    ]


def _label(plan: AnalysisPlan, step_id: str, option_id: str) -> str:
    for step in plan.steps:
        for option in step.options:
            if step.id == step_id and option.id == option_id:
                return f"'{option.label}'"
    return f"'{step_id}'" if step_id else "an unknown step"


def _short(message: str) -> str:
    message = message.split(" | ", 1)[0].strip()
    if len(message) <= MAX_REASON:
        return message
    return message[:MAX_REASON].rsplit(" ", 1)[0] + "…"


def _location(error: str | None) -> tuple[str, str, str]:
    first = (error or "unknown error").strip().splitlines()[0]
    head, sep, message = first.partition(": ")
    step_id, slash, option_id = head.partition("/")
    if not sep or not slash:
        return "", "", first
    return step_id, option_id, message


def _where(plan: AnalysisPlan, error: str | None) -> tuple[str, str]:
    step_id, option_id, message = _location(error)
    if not step_id:
        return "an unknown step", _short(message)
    reason = _short(message)
    if message.startswith("exit code -"):
        reason = f"the process was stopped, {message}"
    return _label(plan, step_id, option_id), reason


def _shared(plan: AnalysisPlan, failed: list[Universe]) -> list[str]:
    defaults = {s.id: s.default.id for s in plan.steps}
    common = set.intersection(
        *({(s, o) for s, o in u.choices.items() if defaults.get(s) != o} for u in failed)
    )
    failing = {_location(u.error)[:2] for u in failed}
    return sorted(_label(plan, s, o) for s, o in common - failing)


def failed_caveat(plan: AnalysisPlan, garden: Garden) -> str | None:
    failed = could_not_run(garden)
    if not failed:
        return None
    groups = Counter(_where(plan, u.error) for u in failed)
    parts = [f"{n} in {label} ({reason})" for (label, reason), n in groups.most_common(MAX_GROUPS)]
    if len(groups) > MAX_GROUPS:
        parts.append(f"{sum(n for _, n in groups.most_common()[MAX_GROUPS:])} elsewhere")
    count = len(failed)
    head = (
        "1 universe could not run and is left out"
        if count == 1
        else f"{count} universes could not run and are left out"
    )
    text = f"{head} of the robustness figure: failed " + "; ".join(parts)
    shared = _shared(plan, failed)
    if shared and count > 1:
        text += f". Every one of them uses {' and '.join(shared)}"
    return text + "."


def untested_decision_caveats(plan: AnalysisPlan, garden: Garden) -> list[str]:
    """A bank_marketing_calls run at 568a627 failed in every universe that handled missing values
    another way: its covariate option listed indicators only the default option creates. The
    robustness figure then said nothing about that decision, and the narrative said it had been
    explored."""
    universes = [u for u in garden.universes.values() if u.kind != "verification"]
    notes = []
    for step in plan.decision_steps:
        tried = [u for u in universes if u.choices.get(step.id, step.default.id) != step.default.id]
        if not tried or any(u.status == "done" for u in tried):
            continue
        used = {u.choices[step.id] for u in tried}
        labels = ", ".join(f"'{o.label}'" for o in step.options if o.id in used)
        notes.append(
            f"The decision '{step.title}' was not tested: every universe with one of its "
            f"alternatives ({labels}) failed, so the robustness figure says nothing about it."
        )
    return notes
