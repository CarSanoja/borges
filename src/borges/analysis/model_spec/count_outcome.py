"""A count model fits the raw count, and the option's text says so.

A hurricanes plan had a transform step that wrote `outcome` as log1p, square root or asinh of the
deaths, and a Poisson option whose text read "regress np.expm1(outcome) if the outcome is
log-transformed else outcome". The translated spec modelled the raw deaths, so the log1p, square
root and asinh Poisson universes were the same number while their text named a transformed
outcome. A Poisson, quasi-Poisson or negative binomial model counts events: a transformed count is
no count, and the sound model is the one on the raw column. The spec is held to the raw column, and
the option's text is rewritten to name it.
"""

from __future__ import annotations

import re

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.model_spec.validate import COUNT_FAMILIES
from borges.analysis.models import AnalysisPlan, Option, Step

TRANSFORM = r"(?:log1p|log|sqrt|asinh|arcsinh|power|expm1|\*\*)"
CONDITIONAL = re.compile(
    r"(?:np\.)?\w+\(\s*outcome\s*\)\s+if\s+(?:the\s+)?outcome\s+is\s+[\w\- ]+?\s+else\s+"
    r"(?:the\s+)?outcome\b",
    re.IGNORECASE,
)
TRANSFORMED_MENTION = re.compile(
    r"\b(?:np\.)?(?:log1p|expm1|log|sqrt|arcsinh|asinh)\(\s*outcome\s*\)"
    r"|\b(?:log|sqrt|square[- ]root|asinh|arcsinh)[\w\- ]*\s+(?:transformed\s+)?outcome\b"
    r"|\btransformed\s+outcome\b|\boutcome\s+is\s+[\w\- ]*transformed\b",
    re.IGNORECASE,
)
ENDOG = re.compile(r"^\s*endog = data\[(['\"])(.+?)\1\]", re.MULTILINE)
COUNT_FIT = re.compile(r"sm\.families\.(?:Poisson|NegativeBinomial)\(")
NAME = re.compile(r"[A-Za-z_]\w*")
AGREED = "Fitted to the raw count {column}, not to a transformed outcome."


def _assignment(name: str) -> re.Pattern[str]:
    target = rf"""(?:\[\s*["']{re.escape(name)}["']\s*\]|(?<![\w.]){re.escape(name)}(?!\w))"""
    return re.compile(rf"{target}\s*=(?!=)\s*([^\n;]*{TRANSFORM}[^\n;]*)", re.IGNORECASE)


def transformed_sources(plan: AnalysisPlan, step: Step, names: list[str]) -> dict[str, str | None]:
    """The produced names an earlier option builds by a transform, with the one dataset column the
    transforms are built from (None when there is not exactly one)."""
    columns = {c.name for c in plan.dataset.columns}
    collected: dict[str, set[str]] = {}
    for earlier in plan.steps:
        if earlier.id == step.id:
            break
        for name in names:
            for option in earlier.options:
                for match in _assignment(name).finditer(option.code or option.spec):
                    found = collected.setdefault(name, set())
                    found.update(w for w in NAME.findall(match.group(1)) if w in columns)
    return {name: next(iter(s)) if len(s) == 1 else None for name, s in collected.items()}


def with_raw_count_outcome(
    spec: ModelSpecOutput, sources: dict[str, str | None]
) -> ModelSpecOutput:
    raw = sources.get(spec.outcome or "")
    if spec.family not in COUNT_FAMILIES or raw is None:
        return spec
    covariates = [c for c in spec.covariates if c != raw]
    return spec.model_copy(update={"outcome": raw, "covariates": covariates})


def count_outcome_problems(spec: ModelSpecOutput, sources: dict[str, str | None]) -> list[str]:
    if spec.family not in COUNT_FAMILIES or spec.outcome not in sources:
        return []
    return [
        f"the {spec.family} model counts events, so it is fitted to the raw count column, not to "
        f"'{spec.outcome}', which an earlier step builds by a transform (log, square root, "
        "asinh): name the raw count column as the outcome"
    ]


def agreed_text(text: str, column: str) -> str:
    rewritten = CONDITIONAL.sub(column, text)
    if rewritten == text and TRANSFORMED_MENTION.search(text) is None:
        return text
    if AGREED.format(column=column) in rewritten:
        return rewritten
    return f"{rewritten.rstrip()} {AGREED.format(column=column)}"


def _raw_count_column(option: Option) -> str | None:
    code = option.code or ""
    if COUNT_FIT.search(code) is None:
        return None
    match = ENDOG.search(code)
    return match.group(2) if match else None


def agree_count_specs(plan: AnalysisPlan) -> list[str]:
    """Rewrite the text of each count model option that names a transformed outcome, to name the
    raw count column its code fits; return the ids of the options rewritten."""
    changed: list[str] = []
    for step in plan.steps:
        if step.kind != "model":
            continue
        for option in step.options:
            column = _raw_count_column(option)
            if column is None:
                continue
            text = agreed_text(option.spec, column)
            if text != option.spec:
                option.spec = text
                changed.append(option.id)
    return changed
