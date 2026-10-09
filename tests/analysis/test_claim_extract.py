from __future__ import annotations

import pytest

from borges.analysis.claim_extract import extract_claim

EVIDENCE = "Education has a significant negative coefficient (-0.11, p < .01)."


def test_the_evidence_text_gives_a_signed_coefficient_with_a_p_bound() -> None:
    claim = extract_claim(EVIDENCE, ["education", "educ"])
    assert claim is not None
    assert (claim.estimate, claim.kind, claim.direction) == (-0.11, "coefficient", "negative")
    assert (claim.p_operator, claim.p_value) == ("<", 0.01)


def test_a_spanish_text_with_a_decimal_comma_is_read() -> None:
    claim = extract_claim("El coeficiente de -0,11 (p < 0.01) es negativo.")
    assert claim is not None and claim.estimate == -0.11 and claim.p_value == 0.01


def test_spanish_coefficient_with_decimal_point() -> None:
    claim = extract_claim("coeficiente de -0.11 (p < 0.01)")
    assert claim is not None and claim.estimate == -0.11 and claim.p_operator == "<"


@pytest.mark.parametrize(
    ("text", "estimate", "kind"),
    [
        ("The odds ratio is 1.45 (95% CI 1.10 to 1.90).", 1.45, "ratio"),
        ("OR = 0.8, p = 0.03", 0.8, "ratio"),
        ("beta = −0.4, p<0.001", -0.4, "coefficient"),
        ("b: 0.25", 0.25, "coefficient"),
        ("The average marginal effect was -0.02 (p = 0.2).", -0.02, "marginal"),
        ("The estimated effect is 3.2, significant at the 5% level.", 3.2, "generic"),
        ("treatment effect (0.5; p=0.04)", 0.5, "generic"),
    ],
)
def test_estimate_forms_are_read_with_their_sign_and_scale(
    text: str, estimate: float, kind: str
) -> None:
    claim = extract_claim(text)
    assert claim is not None
    assert (claim.estimate, claim.kind) == (estimate, kind)


def test_a_p_equals_and_a_significance_level_are_read() -> None:
    equal = extract_claim("coefficient of 0.3 (p = 0.03)")
    level = extract_claim("coefficient of 0.3, significant at the 5% level")
    assert equal is not None and (equal.p_operator, equal.p_value) == ("=", 0.03)
    assert level is not None and (level.p_operator, level.p_value) == ("<", 0.05)


def test_an_interval_is_read_when_it_carries_a_ci_marker() -> None:
    claim = extract_claim("effect of 1.2 (95% CI: 0.4, 2.0)")
    assert claim is not None and (claim.ci_low, claim.ci_high) == (0.4, 2.0)


def test_a_not_significant_claim_is_marked() -> None:
    claim = extract_claim("The coefficient is 0.02 and not statistically significant.")
    assert claim is not None and claim.significant is False


@pytest.mark.parametrize(
    ("text", "direction"),
    [
        ("Education lowers the probability of voting for Clinton.", "negative"),
        ("Education increases turnout.", "positive"),
        ("La educacion disminuye la probabilidad de votar.", "negative"),
        ("Education has no effect on the vote.", "none"),
    ],
)
def test_a_direction_in_words_is_read_when_no_number_is_given(text: str, direction: str) -> None:
    claim = extract_claim(text, ["educ"])
    assert claim is not None and claim.estimate is None and claim.direction == direction


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Logistic regression of vote on educ, age, log income and party ID.",
        "We use 944 respondents from 1996 and fit the model with n = 944.",
        "Education does not reduce the vote.",
        "Age increases and education lowers the vote.",
        "The effect of age on income is small for 5 groups.",
    ],
)
def test_texts_without_a_clear_claim_give_nothing(text: str) -> None:
    assert extract_claim(text, ["education"]) is None


def test_several_estimates_are_ambiguous_without_a_hint() -> None:
    text = "The age coefficient is 0.02. The education coefficient is -0.11."
    assert extract_claim(text) is None


def test_several_estimates_are_resolved_by_the_name_of_the_term() -> None:
    text = "The age coefficient is 0.02. The education coefficient is -0.11."
    claim = extract_claim(text, ["educ"])
    assert claim is not None and claim.estimate == -0.11


def test_the_p_value_of_another_sentence_is_not_borrowed() -> None:
    claim = extract_claim("The coefficient is -0.11. The model fit has p < 0.001 overall.")
    assert claim is not None and claim.p_value is None
