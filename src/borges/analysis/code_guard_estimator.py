from __future__ import annotations

import ast
import re

FAMILY_NAMES = {
    "quasipoisson": re.compile(r"quasi[- ]?(?:poisson|likelihood)", re.IGNORECASE),
    "negbin": re.compile(r"negative[- ]binomial|\bneg[- ]?bin\b|\bNB2?\b", re.IGNORECASE),
    "poisson": re.compile(r"(?<![-\w])(?<!quasi )poisson\b", re.IGNORECASE),
    "logit": re.compile(r"\blogit\b|\blogistic\b", re.IGNORECASE),
}
NEGBIN_CLASSES = frozenset(
    {"NegativeBinomial", "NegativeBinomialP", "negativebinomial", "ZeroInflatedNegativeBinomialP"}
)
POISSON_CLASSES = frozenset(
    {"Poisson", "poisson", "ZeroInflatedPoisson", "GeneralizedPoisson", "PoissonBayesMixedGLM"}
)
LOGIT_CLASSES = frozenset({"Logit", "logit", "Binomial"})
MODEL_NAMES = NEGBIN_CLASSES | POISSON_CLASSES | LOGIT_CLASSES | {"OLS", "ols", "GLM", "glm"}


def named_family(intent: str) -> str | None:
    found = {name for name, pattern in FAMILY_NAMES.items() if pattern.search(intent)}
    if "quasipoisson" in found:
        found.discard("poisson")
    return found.pop() if len(found) == 1 else None


def _identifiers(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def _scales_dispersion(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Call) and any(k.arg == "scale" for k in node.keywords)
        for node in ast.walk(tree)
    )


def _problem(family: str, names: set[str], tree: ast.AST) -> str | None:
    negbin, poisson = bool(names & NEGBIN_CLASSES), bool(names & POISSON_CLASSES)
    if family == "quasipoisson" and (negbin or not poisson or not _scales_dispersion(tree)):
        return (
            "the option names quasi-Poisson, which keeps the Poisson estimate and scales its "
            "standard errors by the Pearson dispersion: fit a Poisson GLM with "
            '.fit(scale="X2"); a negative binomial is a different estimator'
        )
    if family == "negbin" and not negbin:
        return "the option names a negative binomial model but the code fits none"
    if family == "poisson" and (negbin or not poisson):
        return "the option names a Poisson model but the code fits " + (
            "a negative binomial" if negbin else "no Poisson model"
        )
    if family == "logit" and not names & LOGIT_CLASSES:
        return "the option names a logistic model but the code fits no logit"
    return None


def estimator_violations(tree: ast.AST, intent: str) -> list[str]:
    family = named_family(intent) if intent else None
    names = _identifiers(tree)
    if family is None or not names & MODEL_NAMES:
        return []
    problem = _problem(family, names, tree)
    return [problem] if problem else []
