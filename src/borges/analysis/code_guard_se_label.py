"""The standard errors an option names against the covariance its code fits.

The marp_religiosity default at 508fe2e, "OLS with i.i.d. standard errors", fitted cov_type="HC1",
so the adversary's HC1 option was a no-op and the baseline was mislabelled.
"""

from __future__ import annotations

import ast
import re

from borges.analysis.code_guard_statsmodels import (
    FIT_METHODS,
    INSTEAD,
    REFERENCE,
    _call_name,
    robust_intended,
)

NONROBUST = re.compile(
    r"\bi\.?i\.?d\.?(?=\s|$|[,;)])|\bnon-?robust\b|\bhomoske?dastic\b|"
    r"\b(?:classical|conventional|model[- ]based|default)\s+(?:standard errors?|SEs?|covariance)\b",
    re.IGNORECASE,
)
HC_NAMED = re.compile(r"\bHC([0-3])\b")


def _cov_types(tree: ast.AST) -> set[str]:
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node) in FIT_METHODS:
            for keyword in node.keywords:
                value = keyword.value
                if keyword.arg == "cov_type" and isinstance(value, ast.Constant):
                    found.add(str(value.value).upper())
    return found


def se_label_violations(tree: ast.AST, intent: str) -> list[str]:
    types = _cov_types(tree)
    own = INSTEAD.sub("", REFERENCE.split(intent, maxsplit=1)[0])
    if not types:
        return []
    if NONROBUST.search(own) and not robust_intended(intent) and types - {"NONROBUST"}:
        return [
            "the option is described with i.i.d. (model-based) standard errors but the code fits "
            f"cov_type={', '.join(sorted(types))}; fit without cov_type or with "
            'cov_type="nonrobust" so the label matches the standard errors'
        ]
    named = {f"HC{n}" for n in HC_NAMED.findall(own)}
    fitted = {t for t in types if t.startswith("HC")}
    if len(named) == 1 and fitted and not fitted & named:
        want = next(iter(named))
        return [
            f"the option names {want} standard errors but the code fits cov_type="
            f'{", ".join(sorted(fitted))}; use cov_type="{want}"'
        ]
    return []
