from __future__ import annotations

from borges.analysis.models import Option
from borges.analysis.option_signature import same_option, strip_id_prefixes


def opt(option_id: str, label: str = "L", spec: str = "S") -> Option:
    return Option(id=option_id, label=label, rationale="r", spec=spec)


def test_prefixes_are_stripped_repeatedly() -> None:
    assert strip_id_prefixes("adv_alt_opt_wellbeing") == "wellbeing"
    assert strip_id_prefixes("opt_") == "opt_"


def test_same_stripped_id_with_overlapping_label_matches() -> None:
    planner = opt("opt3b", "Psychological well-being mean", "s1")
    adversary = opt("adv_opt3b", "Use psychological well-being mean as outcome", "s2")
    assert same_option(adversary, planner)


def test_coincidental_same_id_with_different_content_does_not_match() -> None:
    planner = opt("opt2b", "Mean of religiosity items", "df['r'] = df[items].mean(axis=1)")
    adversary = opt("adv_opt2b", "First principal component", "PCA on the items")
    assert not same_option(adversary, planner)


def test_same_normalised_label_matches() -> None:
    assert same_option(opt("a", "Mean  of items!", "s1"), opt("b", "mean of items", "s2"))


def test_same_normalised_spec_matches() -> None:
    assert same_option(opt("a", "l1", "Compute the Mean."), opt("b", "l2", "compute  the mean"))


def test_different_options_do_not_match() -> None:
    assert not same_option(opt("a", "l1", "s1"), opt("b", "l2", "s2"))
