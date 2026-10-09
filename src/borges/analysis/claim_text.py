from __future__ import annotations

from borges.analysis.claim_models import ClaimCheck, ClaimedResult

SCALE_NAMES = {
    "ratio": "a ratio",
    "marginal": "a marginal effect",
    "coefficient": "a model coefficient",
    "generic": "an estimate of unstated scale",
}
DIFFERENCE_WORDS = {"sign": "the sign", "significance": "the significance", "magnitude": "the size"}
DIRECTION_WORDS = {"positive": "a positive effect", "negative": "a negative effect"}
SMALL_P = 0.001


def _number(value: float) -> str:
    return f"{value:+.0f}" if abs(value) >= 100 else f"{value:+.3g}"


def _p_text(value: float) -> str:
    return "< 0.001" if value < SMALL_P else f"= {value:.2f}"


def _claimed_text(claim: ClaimedResult) -> str:
    parts = []
    if claim.estimate is not None:
        parts.append(f"{claim.estimate:g}")
    elif claim.direction:
        parts.append(DIRECTION_WORDS.get(claim.direction, "no effect"))
    extras = []
    if claim.p_value is not None and claim.p_operator:
        extras.append(f"p {claim.p_operator} {claim.p_value:g}")
    elif claim.significant is not None:
        extras.append("significant" if claim.significant else "not significant")
    if claim.ci_low is not None and claim.ci_high is not None:
        extras.append(f"CI {claim.ci_low:g} to {claim.ci_high:g}")
    text = " ".join(parts)
    return f"{text} ({', '.join(extras)})" if extras else text


def _verdict(check: ClaimCheck) -> str:
    if check.agrees:
        return "the claim reproduces"
    named = [DIFFERENCE_WORDS[d] for d in check.differences if d in DIFFERENCE_WORDS]
    clauses = []
    if named:
        clauses.append(f"{' and '.join(named)} {'differs' if len(named) == 1 else 'differ'}")
    if "magnitude" in check.differences:
        clauses.append(
            f"the size is outside the reproduced 95% interval "
            f"({check.reproduced_ci_low:.3g} to {check.reproduced_ci_high:.3g})"
        )
    return f"the claim does not reproduce, {'; '.join(clauses)}"


def claim_sentence(check: ClaimCheck) -> str:
    label = f"{check.term} " if check.term else ""
    reproduced = f"{_number(check.reproduced_estimate)} (p {_p_text(check.reproduced_p_value)})"
    lead = (
        f"Your text claims {label}{_claimed_text(check.claimed)}; "
        f"the reproduced analysis gives {reproduced}"
    )
    if check.agrees is None:
        return f"{lead}: the two could not be compared."
    sentence = f"{lead}: {_verdict(check)}."
    if not check.same_scale and check.claimed.estimate is not None:
        sentence += (
            f" The scales may differ (your text gives {SCALE_NAMES[check.claimed.kind]}), "
            "so only the sign and the significance were compared."
        )
    return sentence
