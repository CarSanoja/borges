from __future__ import annotations

from borges.analysis.review_estimand import settle_estimand
from borges.analysis.schemas import ReviewVerdict
from tests.analysis.fakes import make_option


def flagged(faithful: bool) -> ReviewVerdict:
    return ReviewVerdict(
        option_id="married",
        faithful=faithful,
        changes_estimand=True,
        problem="committed differs from the default's grouping",
        quote="Relationship == 4",
    )


def test_an_accepted_option_that_follows_its_spec_keeps_its_place() -> None:
    option = make_option("married")
    option.defensibility = 0.6
    settled = settle_estimand(flagged(True), option)
    assert settled.faithful and not settled.changes_estimand and settled.problem == ""


def test_an_accepted_option_whose_code_departs_goes_to_repair() -> None:
    option = make_option("married")
    option.defensibility = 0.6
    settled = settle_estimand(flagged(False), option)
    assert not settled.faithful and not settled.changes_estimand
    assert settled.problem.startswith("committed differs")


def test_an_option_no_judge_saw_keeps_the_reviewer_flag() -> None:
    assert settle_estimand(flagged(True), make_option("married")).changes_estimand
