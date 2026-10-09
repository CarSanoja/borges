"""Compare the result a user's text claims with the original result Borges reproduced.

Evidence: a text claimed 'education ... coefficient (-0.11, p < .01)' and the reproduction gave
+0.0099 (p = 0.90) without the report ever saying the claim does not reproduce."""

from __future__ import annotations

import re

from borges.analysis.claim_extract import extract_claim
from borges.analysis.claim_models import ClaimCheck, ClaimedResult, ClaimKind
from borges.analysis.claim_patterns import hints_from_metric
from borges.analysis.claim_text import claim_sentence
from borges.analysis.models import AnalysisResult, DecisionRule

RATIO_METRIC = re.compile(r"ratio", re.IGNORECASE)
MARGINAL_METRIC = re.compile(
    r"marginal|percentage[\s-]*points?|probabilit|proportion", re.IGNORECASE
)
COEFFICIENT_METRIC = re.compile(r"coefficient|log[\s-]*odds|logit|slope|beta", re.IGNORECASE)


def metric_kind(metric: str) -> ClaimKind:
    if RATIO_METRIC.search(metric):
        return "ratio"
    if MARGINAL_METRIC.search(metric) and not COEFFICIENT_METRIC.search(metric):
        return "marginal"
    if COEFFICIENT_METRIC.search(metric):
        return "coefficient"
    return "generic"


def _sign(value: float, centre: float) -> int:
    return (value > centre) - (value < centre)


def _claimed_sign(claim: ClaimedResult) -> int | None:
    if claim.estimate is not None and claim.kind == "ratio":
        return _sign(claim.estimate, 1.0) if claim.estimate > 0 else None
    if claim.estimate is not None:
        return _sign(claim.estimate, 0.0) or None
    return {"positive": 1, "negative": -1}.get(claim.direction or "")


def _sign_differs(claim: ClaimedResult, result: AnalysisResult, ratio: bool) -> bool:
    claimed = _claimed_sign(claim)
    reproduced = _sign(result.estimate, 1.0 if ratio else 0.0)
    return claimed is not None and reproduced != 0 and claimed != reproduced


def _claimed_significant(claim: ClaimedResult, alpha: float) -> bool | None:
    value, operator = claim.p_value, claim.p_operator
    if value is None or operator is None:
        return claim.significant
    if operator in ("<", "<="):
        return True if value <= alpha else None
    if operator in (">", ">="):
        return False if value >= alpha else None
    return value < alpha


def _p_bound_broken(claim: ClaimedResult, p_value: float) -> bool:
    if claim.p_value is None:
        return False
    if claim.p_operator in ("<", "<="):
        return p_value >= claim.p_value
    if claim.p_operator in (">", ">="):
        return p_value <= claim.p_value
    return False


def _significance_differs(claim: ClaimedResult, result: AnalysisResult, alpha: float) -> bool:
    claimed = _claimed_significant(claim, alpha)
    if claimed is not None and claimed != (result.p_value < alpha):
        return True
    return _p_bound_broken(claim, result.p_value)


def _magnitude_outside(claim: ClaimedResult, result: AnalysisResult) -> bool:
    if claim.estimate is None:
        return False
    low, high = sorted((result.ci_low, result.ci_high))
    return not (low <= claim.estimate <= high)


def _same_scale(claim: ClaimedResult, result: AnalysisResult, rule: DecisionRule) -> bool:
    reproduced = metric_kind(result.metric or rule.metric)
    return claim.kind != "generic" and reproduced == claim.kind


def _differences(
    claim: ClaimedResult, result: AnalysisResult, alpha: float, same_scale: bool, ratio: bool
) -> list[str]:
    found = []
    if _sign_differs(claim, result, ratio):
        found.append("sign")
    if _significance_differs(claim, result, alpha):
        found.append("significance")
    if same_scale and _magnitude_outside(claim, result) and "sign" not in found:
        found.append("magnitude")
    return found


def _comparable(claim: ClaimedResult) -> bool:
    return (
        _claimed_sign(claim) is not None
        or claim.p_value is not None
        or claim.significant is not None
        or claim.direction == "none"
    )


def compare_claim(
    claim: ClaimedResult, result: AnalysisResult, rule: DecisionRule, term: str | None = None
) -> ClaimCheck:
    same = _same_scale(claim, result, rule)
    ratio = metric_kind(result.metric or rule.metric) == "ratio"
    differs = [] if not _comparable(claim) else _differences(claim, result, rule.alpha, same, ratio)
    agrees = None if not _comparable(claim) else not differs
    check = ClaimCheck(
        claimed=claim,
        term=term,
        reproduced_estimate=result.estimate,
        reproduced_p_value=result.p_value,
        reproduced_ci_low=result.ci_low,
        reproduced_ci_high=result.ci_high,
        n=result.n,
        alpha=rule.alpha,
        agrees=agrees,
        differences=differs,
        same_scale=same,
    )
    check.sentence = claim_sentence(check)
    return check


def check_claim(text: str, result: AnalysisResult, rule: DecisionRule) -> ClaimCheck | None:
    if not text.strip():
        return None
    hints = hints_from_metric(rule.metric)
    claim = extract_claim(text, hints)
    if claim is None:
        return None
    return compare_claim(claim, result, rule, hints[-1] if hints else None)
