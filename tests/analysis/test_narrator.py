from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.analysis.narrator import narrate
from borges.analysis.schemas import NarratorOutput
from borges.garden.models import Report
from borges.llm.client import Role
from tests.analysis.fakes import FakeLLM, make_plan


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
