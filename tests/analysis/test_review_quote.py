from __future__ import annotations

from borges.analysis.review_quote import UNQUOTED, checked_quotes, unsupported
from borges.analysis.schemas import ReviewerOutput, ReviewVerdict
from tests.analysis.fakes import FakeLLM

SPEC = "Create new column 'log_alldeaths_plus1' = np.sqrt(alldeaths); return the DataFrame."
SPECS = {"sqrt": SPEC}
MESSAGES = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]


def verdict(quote: str, faithful: bool = False) -> ReviewVerdict:
    return ReviewVerdict(option_id="sqrt", faithful=faithful, problem="uses sqrt", quote=quote)


def test_a_quote_the_spec_does_not_contain_is_unsupported() -> None:
    assert unsupported(verdict("using np.log1p(alldeaths)"), SPEC)
    assert not unsupported(verdict('"log_alldeaths_plus1 = np.sqrt(alldeaths)."'), SPEC)
    assert not unsupported(verdict(""), SPEC)
    assert not unsupported(verdict("np.log1p", faithful=True), SPEC)


async def test_the_reviewer_is_asked_once_and_its_new_answer_is_used() -> None:
    llm = FakeLLM({"reviewer:s:quote": ReviewerOutput(verdicts=[verdict("", faithful=True)])})
    out = ReviewerOutput(verdicts=[verdict("np.log1p(alldeaths)")])
    [checked] = await checked_quotes(llm, MESSAGES, out, SPECS, "reviewer:s")
    assert checked.faithful and llm.keys() == ["reviewer:s:quote"]
    assert "np.log1p(alldeaths)" in llm.calls[0].messages[-1]["content"]


async def test_a_quote_still_missing_after_the_second_answer_is_dropped() -> None:
    llm = FakeLLM({"reviewer:s:quote": ReviewerOutput(verdicts=[verdict("np.log1p(x)")])})
    out = ReviewerOutput(verdicts=[verdict("np.log1p(alldeaths)")])
    [checked] = await checked_quotes(llm, MESSAGES, out, SPECS, "reviewer:s")
    assert checked.faithful and checked.problem == UNQUOTED.format(quote="np.log1p(x)")


async def test_a_matching_quote_keeps_the_verdict_without_a_call() -> None:
    llm = FakeLLM({})
    out = ReviewerOutput(verdicts=[verdict("np.sqrt(alldeaths)")])
    [checked] = await checked_quotes(llm, MESSAGES, out, SPECS, "reviewer:s")
    assert not checked.faithful and llm.keys() == []
