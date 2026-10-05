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
PENALISED = re.compile(
    r"\bfirth\b|(?<![\w-])penali[sz]ed\b|\bridge (?:regression|penalty|logistic)\b|\blasso\b|"
    r"elastic[- ]net",
    re.IGNORECASE,
)
PENALTY_NAMES = re.compile(r"fit_regularized|firth|penal|jeffreys", re.IGNORECASE)
ROBUST_FIT = re.compile(
    r"\bRLM\b|\bM{1,2}[- ]?estimat\w*|\bHuber(?:'s)?\s+(?:M[- ]?estimat\w*|loss|weights?|T\b|norm)|"
    r"\bTukey(?:'s)?\s+(?:biweight|bisquare)|bisquare|biweight|\brobust (?:linear )?regression\b|"
    r"quantile regression|\bLAD\b|median regression|least absolute deviation",
    re.IGNORECASE,
)
ROBUST_CLASSES = frozenset({"RLM", "rlm", "QuantReg", "quantreg"})
WEIGHTED = re.compile(r"\bweight(?:ed|s|ing)\b|\bWLS\b", re.IGNORECASE)
WEIGHTED_CLASSES = frozenset({"WLS", "wls", "GLS", "gls"})
WEIGHT_KEYWORDS = frozenset({"weights", "freq_weights", "var_weights", "sample_weight"})
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


def _robust(call: ast.Call) -> bool:
    return any(
        k.arg == "cov_type" and isinstance(k.value, ast.Constant) and k.value.value != "nonrobust"
        for k in call.keywords
    )


def _scales_dispersion(tree: ast.AST) -> bool:
    """A red_cards adversary option at d988b34, "Quasi-Poisson regression", fitted
    .fit(scale="X2", cov_type="HC0"): statsmodels ignores the scale under a sandwich covariance,
    so it gave the Poisson HC0 interval to 14 digits."""
    return any(
        isinstance(node, ast.Call)
        and any(k.arg == "scale" for k in node.keywords)
        and not _robust(node)
        for node in ast.walk(tree)
    )


def _problem(family: str, names: set[str], tree: ast.AST) -> str | None:
    negbin, poisson = bool(names & NEGBIN_CLASSES), bool(names & POISSON_CLASSES)
    if family == "quasipoisson" and (negbin or not poisson or not _scales_dispersion(tree)):
        return (
            "the option names quasi-Poisson, which keeps the Poisson estimate and scales its "
            "standard errors by the Pearson dispersion: fit a Poisson GLM with "
            '.fit(scale="X2") and no robust or cluster cov_type (statsmodels ignores the scale '
            "under one); a negative binomial is a different estimator"
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


def _penalty_problem(names: set[str], intent: str) -> list[str]:
    """A Firth, ridge or lasso option fitted by plain maximum likelihood runs another estimator
    under its label."""
    if not PENALISED.search(intent) or any(PENALTY_NAMES.search(name) for name in names):
        return []
    return [
        "the option names a penalised fit (Firth, ridge, lasso or elastic net) but the code fits "
        "an unpenalised model; implement the penalty, for example with fit_regularized, or let "
        "the option fail"
    ]


def _robust_problem(names: set[str], intent: str) -> list[str]:
    """A marp_religiosity adversary option at 1ecb614, "Use MM-estimation robust regression", was
    fitted by OLS and gave the OLS estimate; among 741 recorded model options it was the only one
    that named a robust or quantile fit and fitted neither (Huber-robust standard errors are a
    sandwich, not a robust fit, and do not count)."""
    if not ROBUST_FIT.search(intent) or names & ROBUST_CLASSES:
        return []
    return [
        "the option names a robust or quantile regression (M- or MM-estimation, Huber or Tukey "
        "weights, LAD) but the code fits ordinary least squares; fit it with "
        "statsmodels.api.RLM (or QuantReg for quantiles), or let the option fail"
    ]


def weighted_intent(intent: str) -> bool:
    return bool(WEIGHTED.search(intent)) and not ROBUST_FIT.search(intent)


def _weights_problem(names: set[str], tree: ast.AST, intent: str) -> list[str]:
    """A checkout adversary option at 70a6102, "Weighted OLS by session length", was fitted as an
    unweighted OLS and reported as a no-op; of 10 recorded model options that named weights, 2
    fitted no weighted model."""
    if not weighted_intent(intent) or names & WEIGHTED_CLASSES:
        return []
    keywords = {
        k.arg for node in ast.walk(tree) if isinstance(node, ast.Call) for k in node.keywords
    }
    if keywords & WEIGHT_KEYWORDS:
        return []
    return [
        "the option names a weighted fit but the code fits an unweighted model; fit statsmodels "
        "WLS with weights=..., or a GLM with var_weights or freq_weights, or let the option fail"
    ]


def estimator_violations(tree: ast.AST, intent: str) -> list[str]:
    family = named_family(intent) if intent else None
    names = _identifiers(tree)
    if not names & MODEL_NAMES:
        return []
    penalty = _penalty_problem(names, intent) if intent else []
    robust = _robust_problem(names, intent) if intent else []
    weights = _weights_problem(names, tree, intent) if intent else []
    problem = _problem(family, names, tree) if family is not None else None
    return [*penalty, *robust, *weights, *([problem] if problem else [])]
