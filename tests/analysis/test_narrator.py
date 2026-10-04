from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.analysis.narrative_original import original_sentence
from borges.analysis.narrative_robustness import robustness_sentence
from borges.analysis.narrator import narrate
from borges.analysis.schemas import NarratorOutput
from borges.garden.models import Report
from borges.llm.client import Role
from tests.analysis.fakes import FakeLLM, make_plan
from tests.analysis.test_narrative_flip import checkout_plan, checkout_report


async def test_narrate_returns_text_and_caveats() -> None:
    result = AnalysisResult(estimate=0.4, ci_low=0.1, ci_high=0.7, p_value=0.01, n=100)
    report = Report(
        question="Q?",
        original_verdict="SHIP",
        original_result=result,
        minimal_flip=None,
        influences=[],
        robustness=0.8,
        n_universes=10,
        n_flipped=2,
        narrative="old narrative",
        caveats=["old caveat"],
    )
    robust = robustness_sentence(report)
    first = original_sentence(report)
    out = NarratorOutput(narrative=f"  {first} Plain text. {robust}  ", caveats=["c1"])
    llm = FakeLLM({"narrator": out})
    narrative, caveats = await narrate(llm, make_plan(), report)
    assert narrative == f"{first} Plain text. {robust}"
    assert caveats == ["c1"]
    call = llm.calls[0]
    assert call.role is Role.NARRATOR and call.key == "narrator" and call.max_tokens == 1200
    content = call.messages[1]["content"]
    assert '"robustness":0.8' in content and "SHIP" in content
    assert "old narrative" not in content


SENTENCE = (
    'The minimal flip changes Filter records from "Keep all sessions" '
    'to "Exclude internal sessions".'
)
ROBUST = robustness_sentence(checkout_report())
ORIGINAL = original_sentence(checkout_report())


async def test_flip_sentence_is_requested_verbatim_and_a_faithful_narrative_is_kept() -> None:
    good = f"{ORIGINAL} {SENTENCE} {ROBUST}"
    llm = FakeLLM({"narrator": NarratorOutput(narrative=good, caveats=["c"])})
    narrative, caveats = await narrate(llm, checkout_plan(), checkout_report())
    assert narrative == good and caveats == ["c"]
    assert llm.keys() == ["narrator"]
    assert SENTENCE in llm.calls[0].messages[1]["content"]
    assert "verbatim" in llm.calls[0].messages[1]["content"]


async def test_checkout_narrative_naming_the_wrong_option_is_retried() -> None:
    wrong = f"{ORIGINAL} The flip comes from excluding internal and bot-like sessions."
    fixed = f"{ORIGINAL} {SENTENCE} {ROBUST}"
    llm = FakeLLM(
        {
            "narrator": NarratorOutput(narrative=wrong, caveats=["old"]),
            "narrator:retry": NarratorOutput(narrative=fixed, caveats=["new"]),
        }
    )
    narrative, caveats = await narrate(llm, checkout_plan(), checkout_report())
    assert narrative == fixed and caveats == ["new"]
    assert llm.keys() == ["narrator", "narrator:retry"]
    retry = llm.calls[1].messages[1]["content"]
    assert "rejected" in retry and "bot-like" in retry


async def test_missing_sentence_after_the_retry_is_inserted_as_second_sentence() -> None:
    bad = f"{ORIGINAL} {ROBUST}"
    llm = FakeLLM(
        {
            "narrator": NarratorOutput(narrative=bad),
            "narrator:retry": NarratorOutput(narrative=bad),
        }
    )
    narrative, _ = await narrate(llm, checkout_plan(), checkout_report())
    assert narrative == f"{ORIGINAL} {SENTENCE} {ROBUST}"


async def test_failed_retry_falls_back_to_insertion() -> None:
    bad = f"{ORIGINAL} It excludes internal and bot-like sessions."
    llm = FakeLLM({"narrator": NarratorOutput(narrative=bad, caveats=["k"])})
    narrative, caveats = await narrate(llm, checkout_plan(), checkout_report())
    assert narrative == f"{ORIGINAL} {SENTENCE} {ROBUST}"
    assert caveats == ["k"]
    assert llm.keys() == ["narrator", "narrator:retry"]


async def test_retry_that_repairs_only_the_label_still_gets_the_sentence() -> None:
    llm = FakeLLM(
        {
            "narrator": NarratorOutput(narrative=f"{ORIGINAL} Second. {ROBUST}"),
            "narrator:retry": NarratorOutput(narrative=f"{ORIGINAL} {SENTENCE} Second. {ROBUST}"),
        }
    )
    narrative, _ = await narrate(llm, checkout_plan(), checkout_report())
    assert narrative == f"{ORIGINAL} {SENTENCE} Second. {ROBUST}"


async def test_fallback_removes_sentences_that_name_another_option_of_the_flipped_step() -> None:
    bad = f"{ORIGINAL} The flip comes from excluding internal and bot-like sessions. {ROBUST}"
    llm = FakeLLM({"narrator": NarratorOutput(narrative=bad)})
    narrative, _ = await narrate(llm, checkout_plan(), checkout_report())
    assert narrative == f"{ORIGINAL} {SENTENCE} {ROBUST}"
    assert "bot-like" not in narrative


async def test_an_estimate_on_the_log_scale_is_never_read_as_additional_units() -> None:
    from tests.garden.test_outcome_scale import garden

    result = AnalysisResult(estimate=0.0293, ci_low=-0.05, ci_high=0.11, p_value=0.47, n=93)
    report = Report(
        question="Q?",
        original_verdict="NO CLEAR EVIDENCE",
        original_result=result,
        minimal_flip=None,
        influences=[],
        robustness=1.0,
        n_universes=3,
        n_flipped=0,
    )
    bad = (
        "No clear evidence. The estimate was 0.029 additional deaths per unit. "
        f"{robustness_sentence(report)}"
    )
    llm = FakeLLM({"narrator": NarratorOutput(narrative=bad, caveats=[])})
    scaled = garden({"kind": "log1p", "column": "alldeaths"})
    narrative, _ = await narrate(llm, make_plan(), report, scaled)
    assert llm.keys() == ["narrator", "narrator:retry"]
    assert (
        "Scale of the estimate: The original analysis is a model of log1p(alldeaths)"
        in (llm.calls[0].messages[1]["content"])
    )
    assert "on the log scale: about 3.0% more alldeaths" in narrative


async def test_an_instruction_copied_next_to_a_verbatim_sentence_is_dropped() -> None:
    from borges.analysis.prompts.narrator import ORIGINAL_RULE, ROBUST_RULE

    echoed = f"{ORIGINAL} {ORIGINAL_RULE} {SENTENCE} {ROBUST} {ROBUST_RULE}"
    llm = FakeLLM({"narrator": NarratorOutput(narrative=echoed, caveats=[])})
    narrative, _ = await narrate(llm, checkout_plan(), checkout_report())
    assert narrative == f"{ORIGINAL} {SENTENCE} {ROBUST}"
    prompt = llm.calls[0].messages[1]["content"]
    assert f"{ROBUST_RULE} Include the sentence below verbatim" in prompt
    assert f"\n{ROBUST}\n" in prompt


async def test_a_correct_draft_that_leaves_out_a_required_sentence_is_kept_and_completed() -> None:
    est = checkout_report().original_result.estimate
    draft = (
        f"The original analysis estimated a lift of {est:.2f} percentage points and shipped. "
        f"{SENTENCE} Only the filter moves the estimate."
    )
    llm = FakeLLM({"narrator": NarratorOutput(narrative=draft, caveats=[])})
    narrative, _ = await narrate(llm, checkout_plan(), checkout_report())
    assert llm.keys() == ["narrator"]
    assert narrative == f"{draft} {ROBUST}"
