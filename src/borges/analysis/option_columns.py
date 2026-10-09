"""Columns an option names that the data does not have.

A fair adversary proposed ctx['covariates'] with selfesteem and depression, columns that do not
exist; the judge scored the option 0.6 and it failed later in the sandbox with an opaque numpy
error (r_20261009T003732_8fbd3d). A statecrime WLS option promising population weights ran as plain
OLS. The names an option sets in its ctx entries, and the weights it promises, are checked against
the profiled columns (case-insensitive: the upload lower-cases them) before the option is judged.
"""

from __future__ import annotations

import re

from borges.analysis.code_guard_ctx import CREATED, ctx_writes
from borges.analysis.models import AnalysisPlan, Option

NAMING_KEYS = frozenset(
    {"covariates", "outcome", "weights", "weight", "exposure", "cluster", "cluster_by"}
)
QUOTED = re.compile(r"""["']([^"'\s]+)["']""")
WEIGHT_COLUMN = re.compile(
    r"""\bweight(?:s|ed|ing)?\b(?:\s+(?:by|using|from|with|on|column|variable|named|called|of|the))*"""
    r"""\s*[=:(]?\s*(?:df\s*\[\s*)?["'](\w+)["']""",
    re.IGNORECASE,
)
WEIGHT_PROMISE = re.compile(
    r"\b(?:population|sampling|survey|sample|probability|design|frequency)\s+weights?\b",
    re.IGNORECASE,
)
WEIGHT_HINTS = ("weight", "wt", "pop", "freq")


def known_columns(plan: AnalysisPlan, option: Option | None = None) -> set[str]:
    """Dataset columns, columns a step produces or an option's code creates, and any name another
    option of the plan puts in quotes (a column built in prose that no code assignment shows)."""
    others = [o for s in plan.steps for o in s.options if option is None or o.spec != option.spec]
    created = {c for o in others for c in CREATED.findall(o.code or o.spec)}
    produced = {name for s in plan.steps for name in s.produces}
    quoted = {n for o in others if o.origin == "planner" for n in QUOTED.findall(o.spec)}
    return {c.name.lower() for c in plan.dataset.columns} | {
        n.lower() for n in created | produced | quoted
    }


def _named_columns(spec: str) -> list[str]:
    names: list[str] = []
    for key, value in ctx_writes(spec).items():
        if key not in NAMING_KEYS:
            continue
        listed = re.match(r"\s*\[([^\]]*)\]", value)
        names.extend(QUOTED.findall(listed.group(1) if listed else value))
    names.extend(WEIGHT_COLUMN.findall(spec))
    return names


def missing_columns(plan: AnalysisPlan, option: Option) -> list[str]:
    """Columns the option names that are not in the data, in order of first mention."""
    known = known_columns(plan, option)
    missing: list[str] = []
    for name in _named_columns(option.spec):
        if name.lower() not in known and name not in missing:
            missing.append(name)
    return missing


def promises_absent_weights(plan: AnalysisPlan, option: Option) -> bool:
    if WEIGHT_COLUMN.search(option.spec) or not WEIGHT_PROMISE.search(option.spec):
        return False
    return not any(hint in name for name in known_columns(plan, option) for hint in WEIGHT_HINTS)


def missing_reason(plan: AnalysisPlan, option: Option) -> str | None:
    missing = missing_columns(plan, option)
    if missing:
        return "names columns not in the data: " + ", ".join(missing)
    if promises_absent_weights(plan, option):
        return "promises weights but the data has no weight column"
    return None
