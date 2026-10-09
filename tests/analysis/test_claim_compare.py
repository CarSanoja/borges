from __future__ import annotations

from borges.analysis.claim_compare import check_claim, compare_claim
from borges.analysis.claim_models import ClaimedResult
from borges.analysis.models import AnalysisResult, Comparator, DecisionRule

TEXT = "Education has a significant negative coefficient (-0.11, p < .01)."
RULE = DecisionRule(
    metric="coefficient of education (educ) in a logistic regression of the vote (vote) on educ",
    comparator=Comparator.LT,
    alpha=0.01,
)
REPRODUCED = AnalysisResult(estimate=0.0099, ci_low=-0.14, ci_high=0.16, p_value=0.896, n=944)


def test_the_evidence_claim_does_not_reproduce() -> None:
    check = check_claim(TEXT, REPRODUCED, RULE)
    assert check is not None and check.agrees is False
    assert check.differences == ["sign", "significance"]
    assert check.same_scale
    assert check.sentence == (
        "Your text claims educ -0.11 (p < 0.01); the reproduced analysis gives +0.0099 "
        "(p = 0.90): the claim does not reproduce, the sign and the significance differ."
    )


def test_a_claim_that_matches_the_reproduction_agrees() -> None:
    result = AnalysisResult(estimate=-0.113, ci_low=-0.19, ci_high=-0.03, p_value=0.004, n=944)
    check = check_claim(TEXT, result, RULE)
    assert check is not None and check.agrees is True and check.differences == []
    assert check.sentence.endswith("the claim reproduces.")


def test_a_magnitude_outside_the_interval_with_the_same_sign_is_reported() -> None:
    result = AnalysisResult(estimate=-0.5, ci_low=-0.7, ci_high=-0.3, p_value=0.001, n=944)
    check = check_claim("coefficient of -0.11", result, RULE)
    assert check is not None and check.differences == ["magnitude"]
    assert "outside the reproduced 95% interval (-0.7 to -0.3)" in check.sentence


def test_a_significant_claim_against_a_non_significant_result_differs_at_the_users_alpha() -> None:
    result = AnalysisResult(estimate=-0.11, ci_low=-0.3, ci_high=0.08, p_value=0.2, n=100)
    check = check_claim("coefficient of -0.11 (p < 0.01)", result, RULE)
    assert check is not None and check.differences == ["significance"]


def test_a_non_significant_claim_against_a_significant_result_differs() -> None:
    result = AnalysisResult(estimate=0.3, ci_low=0.1, ci_high=0.5, p_value=0.003, n=100)
    check = check_claim("The coefficient is 0.3 and not significant.", result, RULE)
    assert check is not None and check.differences == ["significance"]


def test_an_odds_ratio_is_compared_only_by_sign_and_significance_on_a_log_odds_scale() -> None:
    result = AnalysisResult(estimate=-0.1, ci_low=-0.2, ci_high=-0.01, p_value=0.02, n=100)
    check = check_claim("OR = 1.5, p = 0.001", result, RULE)
    assert check is not None and not check.same_scale
    assert check.differences == ["sign", "significance"]
    assert "scales may differ" in check.sentence


def test_an_odds_ratio_below_one_agrees_in_sign_with_a_negative_coefficient() -> None:
    result = AnalysisResult(estimate=-0.1, ci_low=-0.2, ci_high=-0.01, p_value=0.001, n=100)
    check = check_claim("OR = 0.9, p < 0.01", result, RULE)
    assert check is not None and check.agrees is True and not check.same_scale


def test_ratios_on_both_sides_compare_around_one() -> None:
    rule = DecisionRule(metric="odds ratio of treatment", alpha=0.05)
    result = AnalysisResult(estimate=0.8, ci_low=0.6, ci_high=0.95, p_value=0.01, n=100)
    check = check_claim("OR = 1.5, p < 0.05", result, rule)
    assert check is not None and check.same_scale
    assert check.differences == ["sign"]


def test_a_direction_in_words_is_compared_with_the_sign() -> None:
    check = check_claim("Education lowers the vote for Clinton.", REPRODUCED, RULE)
    assert check is not None and check.differences == ["sign"]


def test_no_effect_claim_against_a_significant_result_differs() -> None:
    result = AnalysisResult(estimate=0.3, ci_low=0.1, ci_high=0.5, p_value=0.001, n=100)
    check = check_claim("Education has no effect on the vote.", result, RULE)
    assert check is not None and check.differences == ["significance"]


def test_a_text_without_a_claim_gives_no_check() -> None:
    assert check_claim("Logistic regression of vote on educ.", REPRODUCED, RULE) is None
    assert check_claim("", REPRODUCED, RULE) is None


def test_a_claim_with_nothing_to_compare_gives_none() -> None:
    claim = ClaimedResult(estimate=0.0, kind="coefficient")
    check = compare_claim(claim, REPRODUCED, RULE)
    assert check.agrees is None and "could not be compared" in check.sentence
