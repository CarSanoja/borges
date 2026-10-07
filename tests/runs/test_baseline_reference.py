from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.runs import baseline_reference
from borges.runs.baseline_reference import agreed_reference, same_result
from tests.analysis.fakes import make_plan

A = AnalysisResult(estimate=-1.623, ci_low=-2.7236, ci_high=-0.5224, p_value=0.0038, n=303)
B = AnalysisResult(estimate=-1.5901, ci_low=-2.6916, ci_high=-0.4886, p_value=0.0047, n=301)


def test_results_agree_only_with_the_same_n_and_nearly_the_same_numbers() -> None:
    assert same_result(A, A.model_copy(update={"estimate": -1.6231, "p_value": 0.5}))
    assert not same_result(A, A.model_copy(update={"n": 302}))
    assert not same_result(A, A.model_copy(update={"ci_high": -0.51}))


def scripted(monkeypatch, outcomes: dict[int, AnalysisResult | None]) -> list[int]:
    asked: list[int] = []

    async def fake(llm, executor, plan, attempt, fits=None):
        asked.append(attempt)
        result = outcomes[attempt]
        return result, f"code {attempt}" if result is not None else "it failed"

    monkeypatch.setattr(baseline_reference, "reference_result", fake)
    return asked


async def test_two_agreeing_implementations_need_no_third(monkeypatch) -> None:
    asked = scripted(monkeypatch, {1: A, 2: A, 3: B})
    found = await agreed_reference(None, object(), make_plan())
    assert sorted(asked) == [1, 2] and found.agreed == (A, "code 1")


async def test_a_disagreement_or_a_failure_brings_in_a_third(monkeypatch) -> None:
    asked = scripted(monkeypatch, {1: A, 2: B, 3: A})
    found = await agreed_reference(None, object(), make_plan())
    assert sorted(asked) == [1, 2, 3] and found.agreed == (A, "code 1")
    asked = scripted(monkeypatch, {1: None, 2: B, 3: B})
    found = await agreed_reference(None, object(), make_plan())
    assert found.agreed == (B, "code 2") and found.errors == ["it failed"]
