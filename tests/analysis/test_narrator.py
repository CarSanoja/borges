from __future__ import annotations

from borges.analysis.models import AnalysisResult
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
    out = NarratorOutput(narrative="  Plain text.  ", caveats=["c1"])
    llm = FakeLLM({"narrator": out})
    narrative, caveats = await narrate(llm, make_plan(), report)
    assert narrative == "Plain text."
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


async def test_flip_sentence_is_requested_verbatim_and_a_faithful_narrative_is_kept() -> None:
    good = f"The verdict is SHIP. {SENTENCE} Robustness is 50%."
    llm = FakeLLM({"narrator": NarratorOutput(narrative=good, caveats=["c"])})
    narrative, caveats = await narrate(llm, checkout_plan(), checkout_report())
    assert narrative == good and caveats == ["c"]
    assert llm.keys() == ["narrator"]
    assert SENTENCE in llm.calls[0].messages[1]["content"]
    assert "verbatim" in llm.calls[0].messages[1]["content"]


async def test_checkout_narrative_naming_the_wrong_option_is_retried() -> None:
    wrong = "The verdict is SHIP. The flip comes from excluding internal and bot-like sessions."
    fixed = f"The verdict is SHIP. {SENTENCE} Robustness is 50%."
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
    bad = "The verdict is SHIP. Robustness is 50%."
    llm = FakeLLM(
        {
            "narrator": NarratorOutput(narrative=bad),
            "narrator:retry": NarratorOutput(narrative=bad),
        }
    )
    narrative, _ = await narrate(llm, checkout_plan(), checkout_report())
    assert narrative == f"The verdict is SHIP. {SENTENCE} Robustness is 50%."


async def test_failed_retry_falls_back_to_insertion() -> None:
    bad = "The verdict is SHIP. It excludes internal and bot-like sessions."
    llm = FakeLLM({"narrator": NarratorOutput(narrative=bad, caveats=["k"])})
    narrative, caveats = await narrate(llm, checkout_plan(), checkout_report())
    assert narrative == f"The verdict is SHIP. {SENTENCE}"
    assert caveats == ["k"]
    assert llm.keys() == ["narrator", "narrator:retry"]


async def test_retry_that_repairs_only_the_label_still_gets_the_sentence() -> None:
    llm = FakeLLM(
        {
            "narrator": NarratorOutput(narrative="First. Second."),
            "narrator:retry": NarratorOutput(narrative=f"First. {SENTENCE} Second."),
        }
    )
    narrative, _ = await narrate(llm, checkout_plan(), checkout_report())
    assert narrative == f"First. {SENTENCE} Second."


async def test_fallback_removes_sentences_that_name_another_option_of_the_flipped_step() -> None:
    bad = (
        "The verdict is SHIP. The flip comes from excluding internal and bot-like sessions. "
        "Robustness is 50%."
    )
    llm = FakeLLM({"narrator": NarratorOutput(narrative=bad)})
    narrative, _ = await narrate(llm, checkout_plan(), checkout_report())
    assert narrative == f"The verdict is SHIP. {SENTENCE} Robustness is 50%."
    assert "bot-like" not in narrative
