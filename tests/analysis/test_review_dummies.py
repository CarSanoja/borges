from __future__ import annotations

from borges.analysis.review_dummies import IGNORED_DUMMIES, apply_dummy_contract
from borges.analysis.schemas import ReviewVerdict
from borges.analysis.smoke_core import _trace_effects

NOTE = (
    "ctx['covariates'] named dummies get_dummies did not build (platform_android); the ones it "
    "built are listed instead (platform_ios, platform_web): the reference level does not change "
    "the exposure's estimate"
)
CHECKOUT = (
    "The spec requires creating dummy variables for platform with drop_first=True and setting "
    "ctx['covariates'] = ['platform_ios', 'platform_android']. However, the code produced columns "
    "'platform_ios' and 'platform_web', meaning it did not drop the first category correctly. "
    "This contradicts the spec's requirement for ['platform_ios', 'platform_android'] as "
    "covariates."
)


def verdict(problem: str) -> ReviewVerdict:
    return ReviewVerdict(option_id="o", faithful=False, changes_estimand=False, problem=problem)


def test_a_complaint_about_the_listed_dummies_alone_is_dropped() -> None:
    out = apply_dummy_contract(verdict(CHECKOUT), NOTE)
    assert out.faithful and out.problem == IGNORED_DUMMIES


def test_another_complaint_survives_and_no_note_changes_nothing() -> None:
    mixed = CHECKOUT + " The code also drops every row with day > 10."
    out = apply_dummy_contract(verdict(mixed), NOTE)
    assert not out.faithful and out.problem == "The code also drops every row with day > 10."
    assert apply_dummy_contract(verdict(CHECKOUT), None).faithful is False


def test_the_trace_note_reaches_the_effects() -> None:
    line = '{"step_id": "s", "note": "' + NOTE.replace("'", "'") + '", "fingerprint": "ab"}'
    effects = _trace_effects("BORGES_TRACE " + line)
    assert effects == {"fingerprint": "ab", "harness_note": NOTE}
    assert _trace_effects('BORGES_TRACE {"note": "other", "fingerprint": "ab"}') == {
        "fingerprint": "ab"
    }
