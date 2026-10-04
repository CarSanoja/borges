from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan, Step

QUOTED = re.compile(r"""["']([^"']+)["']""")
CTX_LIST = re.compile(r"""covariates["']\]\s*(?:=|\.extend\(|\+=)\s*(\[[^\]]*\]|\w+)""")


def _literals(text: str) -> set[str]:
    return set(QUOTED.findall(text))


def _code_names(code: str) -> set[str]:
    found: set[str] = set()
    for target in CTX_LIST.findall(code):
        if target.startswith("["):
            found |= _literals(target)
            continue
        for body in re.findall(rf"\b{re.escape(target)}\s*=\s*(\[[^\]]*\])", code):
            found |= _literals(body)
    return found


def _spec_names(text: str, available: list[str]) -> set[str]:
    return {n for n in available if re.search(rf"(?<![\w]){re.escape(n)}(?![\w])", text)}


def ctx_covariate_names(plan: AnalysisPlan, step: Step, available: list[str]) -> list[str]:
    names: set[str] = set()
    for earlier in plan.steps:
        if earlier.id == step.id:
            break
        for option in earlier.options:
            if option.code and "covariates" in option.code:
                names |= _code_names(option.code)
            if "covariates" in option.spec:
                names |= _spec_names(option.spec, available)
    return sorted(n for n in names if n in available)
