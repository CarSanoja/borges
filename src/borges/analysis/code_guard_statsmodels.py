from __future__ import annotations

import ast
import re

from borges.analysis.models import Option

MODEL_CLASSES = frozenset(
    {
        "OLS",
        "WLS",
        "GLS",
        "GLSAR",
        "Logit",
        "Probit",
        "Poisson",
        "NegativeBinomial",
        "GLM",
        "MNLogit",
        "QuantReg",
        "RLM",
        "MixedLM",
        "ols",
        "wls",
        "gls",
        "logit",
        "probit",
        "poisson",
        "glm",
        "quantreg",
        "rlm",
        "mnlogit",
        "mixedlm",
        "negativebinomial",
    }
)
FIT_METHODS = frozenset({"fit", "fit_regularized"})
WEIGHTED_CLASSES = frozenset({"WLS", "wls"})
CONSTRUCTOR_KEYWORDS = ("cov_type", "cov_kwds", "robust")
REFERENCE = re.compile(r"\s\([A-Za-z][\w-]*: ")
INSTEAD = re.compile(r"\b(?:instead of|rather than|not)\b[^.,;]*", re.IGNORECASE)
COVARIANCE_HELPERS = ("cov_hc0", "cov_hc1", "cov_hc2", "cov_hc3", "cov_cluster", "cov_white")
ROBUST_INTENT = re.compile(
    r"(?<!non-)(?<!non )(?<!not )"
    r"(\bHC[0-3]\b|heteroske?dasticity[- ]?(robust|consistent)|"
    r"\brobust\s+(standard\s+errors?|SEs?|covariance|std)|"
    r"\bcluster(?:ed)?(\s+|-)?(robust\s+)?(standard\s+errors?|SEs?)|\bclustered\s+(?:by|on|at)\b|"
    r"\bcluster[- ]robust|\bsandwich\b)",
    re.IGNORECASE,
)


def robust_intended(intent: str) -> bool:
    """Robust errors named in the option's own words. A bank option at 9b95d04, "model-based SEs:
    same as opt_logit but use default covariance instead of cluster-robust", was refused for
    lacking cov_type because of the words it negated and of the referenced option's spec."""
    own = REFERENCE.split(intent, maxsplit=1)[0]
    return ROBUST_INTENT.search(INSTEAD.sub("", own)) is not None


def option_intent(option: Option) -> str:
    return f"{option.label} {option.spec}"


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _keywords(node: ast.Call) -> set[str]:
    return {k.arg for k in node.keywords if k.arg is not None}


def _has_kwargs_splat(node: ast.Call) -> bool:
    return any(k.arg is None for k in node.keywords)


def _weights_violations(node: ast.Call, name: str) -> list[str]:
    if "weights" not in _keywords(node) or name in WEIGHTED_CLASSES:
        return []
    return [
        f"line {node.lineno}: weights= passed to {name} is silently ignored by statsmodels, so "
        "the fit is unweighted; for frequency weights fit sm.GLM(endog, exog, family=..., "
        "freq_weights=w), for analytic weights sm.WLS(endog, exog, weights=w) or GLM var_weights"
    ]


def _constructor_violations(node: ast.Call, name: str) -> list[str]:
    bad = [k for k in CONSTRUCTOR_KEYWORDS if k in _keywords(node)]
    if not bad:
        return _weights_violations(node, name)
    names = ", ".join(f"{k}=" for k in bad)
    return [
        f"line {node.lineno}: {names} passed to the {name} constructor is silently ignored by "
        f"statsmodels, so the reported standard errors stay classical; pass the covariance "
        f'option to the fit call instead, for example {name}(y, X).fit(cov_type="HC3")',
        *_weights_violations(node, name),
    ]


def _fit_violations(node: ast.Call) -> list[str]:
    keys = _keywords(node)
    violations = []
    if "robust" in keys:
        violations.append(
            f"line {node.lineno}: fit() has no 'robust' option and ignores it; use "
            f'.fit(cov_type="HC3") (or "HC1", "cluster" with cov_kwds) for robust standard errors'
        )
    if "cov_kwds" in keys and "cov_type" not in keys and not _has_kwargs_splat(node):
        violations.append(
            f"line {node.lineno}: cov_kwds without cov_type is silently ignored; "
            f"add cov_type to the same fit() call"
        )
    return violations


def _link_violations(node: ast.Call) -> list[str]:
    """statsmodels refuses a link class: Binomial(link=links.Logit) raises TypeError."""
    return [
        f"line {node.lineno}: link= takes an instance of a link class, not the class; write "
        f"link={ast.unparse(k.value)}() (with the parentheses)"
        for k in node.keywords
        if k.arg == "link" and isinstance(k.value, ast.Attribute | ast.Name)
    ]


def _sets_covariance(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _call_name(node)
            if name in FIT_METHODS and ("cov_type" in _keywords(node) or _has_kwargs_splat(node)):
                return True
            if name == "get_robustcov_results":
                return True
            if name is not None and name.startswith(COVARIANCE_HELPERS):
                return True
    return False


def statsmodels_violations(tree: ast.AST, intent: str = "") -> list[str]:
    violations: list[str] = []
    uses_model = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        violations.extend(_link_violations(node))
        if name in MODEL_CLASSES:
            uses_model = True
            violations.extend(_constructor_violations(node, name))
        elif name in FIT_METHODS:
            violations.extend(_fit_violations(node))
    if uses_model and robust_intended(intent) and not _sets_covariance(tree):
        violations.append(
            "the option is described as using robust or clustered standard errors but the code "
            'never passes cov_type to fit(); call .fit(cov_type="HC3") (or "HC1", or "cluster" '
            "with cov_kwds={'groups': ...}) so the label matches the standard errors"
        )
    return violations
