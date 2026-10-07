"""A model step whose spec builds a term of its own formula.

fertility_vote on 7 October, run 39: the model step's spec read "formula = 'Vote ~ high +
committed + high:committed' ... where high = (cycle_day >= 7) & (cycle_day <= 14)". The model
coder fits the exposure as a column the earlier steps pass on, so it took cycle_day as the exposure,
every model option failed on it, and repairs of the earlier steps could not help. A term assigned
in a model spec and named in its formula, that neither the data nor any earlier step produces, is
sent back to the planner to be built in a step before the model when it is defined by a range or
comparison (a level of a column, such as variant == 'B', the model can read itself).
"""

from __future__ import annotations

import re

from borges.analysis.models import DatasetProfile
from borges.analysis.planner_carried import ASSIGNED
from borges.analysis.schemas import PlannedStep

TERM = r"\w+(?:\([^)]*\))?"
FORMULA = re.compile(rf"~\s*({TERM}(?:\s*[+*:\-]\s*{TERM})*)")
WORD = re.compile(r"[A-Za-z_]\w*")
RANGE = re.compile(r"[<>]|\bbetween\b")


def _definition(spec: str, name: str) -> str:
    found = re.search(rf"(?<![\w.'\"]){re.escape(name)}\s*=(?!=)\s*([^;\n]*?)(?=\.\s|;|\n|$)", spec)
    return found.group(1) if found else ""


def built_terms(spec: str, available: set[str]) -> list[str]:
    """Terms of the formula that the spec defines by a range or comparison of other columns,
    which the model cannot read as a level of a column."""
    terms = {w for part in FORMULA.findall(spec) for w in WORD.findall(part)}
    return sorted(
        n
        for n in set(ASSIGNED.findall(spec))
        if n in terms and n not in available and RANGE.search(_definition(spec, n))
    )


def model_terms_shortfall(steps: list[PlannedStep], profile: DatasetProfile) -> str | None:
    available = {c.name for c in profile.columns}
    for step in steps:
        if step.kind != "model":
            available |= set(step.produces)
    found = {
        f"{s.id}.{o.id}": terms
        for s in steps
        if s.kind == "model"
        for o in s.options
        if (terms := built_terms(o.spec, available))
    }
    if not found:
        return None
    listed = "; ".join(f"{where}: {', '.join(terms)}" for where, terms in found.items())
    return (
        "These model options build a term of their own formula from other columns "
        f"({listed}). The model step reads its exposure, groups and covariates as columns the "
        "earlier steps pass on: build each such term in a feature step before the model, list it "
        "in that step's produces, and have the model options read it."
    )
