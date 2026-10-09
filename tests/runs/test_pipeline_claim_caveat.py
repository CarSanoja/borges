from __future__ import annotations

from borges.analysis.claim_compare import check_claim
from borges.analysis.models import AnalysisResult, Comparator, DecisionRule
from borges.runs.baseline_messages import CONFIRMED_GAPS
from borges.runs.pipeline_caveats import claim_caveats, merge_caveats

RULE = DecisionRule(
    metric="coefficient of education (educ) in a logistic regression",
    comparator=Comparator.LT,
    alpha=0.01,
)
TEXT = "Education has a significant negative coefficient (-0.11, p < .01)."


def test_a_claim_that_does_not_reproduce_is_the_first_caveat() -> None:
    result = AnalysisResult(estimate=0.0099, ci_low=-0.14, ci_high=0.16, p_value=0.896, n=944)
    check = check_claim(TEXT, result, RULE)
    caveats = merge_caveats(claim_caveats(check), ["Only the default analysis ran."])
    assert caveats[0].startswith("Your text claims educ -0.11")
    assert "the claim does not reproduce" in caveats[0]


def test_a_claim_that_reproduces_adds_no_caveat() -> None:
    result = AnalysisResult(estimate=-0.11, ci_low=-0.2, ci_high=-0.02, p_value=0.003, n=944)
    assert claim_caveats(check_claim(TEXT, result, RULE)) == []
    assert claim_caveats(None) == []


def test_the_independent_implementation_caveat_does_not_read_as_confirming_the_claim() -> None:
    text = CONFIRMED_GAPS.format(n=1, s="", they="it does")
    assert "not the numbers your text claims" in text
