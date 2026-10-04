from __future__ import annotations

from pathlib import Path

import pytest

from borges.analysis.coder import code_plan
from borges.analysis.models import CodingSummary
from borges.analysis.schemas import CoderOutput
from borges.llm.client import BudgetExceeded, LLMError
from tests.analysis.fakes import FakeLLM, make_plan
from tests.analysis.test_coder_smoke import (
    ESTIMATE,
    KEEP,
    TRIM_FIXED,
    Recorder,
    config,
    passing_guard,
)

__all__ = ["passing_guard"]

BROKEN = 'def estimate(df, ctx):\n    raise AttributeError("no attribute norm")'


def scripted(**overrides: str) -> dict[str, CoderOutput]:
    base = {
        "coder:d1.keep": KEEP,
        "coder:d1.trim": TRIM_FIXED,
        "coder:m1.ols": BROKEN,
        "coder:m1.ols:smoke1": BROKEN,
        "coder:m1.ols:smoke2": BROKEN,
        "coder:m1.welch": BROKEN,
        "coder:m1.welch:smoke1": BROKEN,
        "coder:m1.welch:smoke2": BROKEN,
    }
    return {key: CoderOutput(code=code) for key, code in {**base, **overrides}.items()}


async def test_fresh_recode_rescues_the_default(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(**{"coder:m1.ols:recode": ESTIMATE}))
    recorder = Recorder()
    summary = CodingSummary()
    coded = await code_plan(llm, make_plan(), smoke=config(tmp_path, recorder), summary=summary)
    model = coded.step("m1")
    assert model.default.id == "ols"
    assert model.default.code == ESTIMATE
    recode_call = next(c for c in llm.calls if c.key == "coder:m1.ols:recode")
    prompt = recode_call.messages[-1]["content"]
    assert "write new code" in prompt and "no attribute norm" in prompt
    assert prompt.count("no attribute norm") >= 3
    assert any(e[1] == "ols" and e[2] == "repaired" for e in recorder.events)


async def test_sibling_is_promoted_when_recode_fails(tmp_path: Path) -> None:
    llm = FakeLLM(
        scripted(
            **{
                "coder:m1.ols:recode": BROKEN,
                "coder:m1.welch": ESTIMATE,
            }
        )
    )
    recorder = Recorder()
    cfg = config(tmp_path, recorder)
    coded = await code_plan(llm, make_plan(), smoke=cfg)
    model = coded.step("m1")
    assert [o.id for o in model.options] == ["welch"]
    assert model.default.id == "welch"
    note = next(e[4] for e in recorder.events if e[1] == "welch" and e[4])
    assert note.startswith("promoted to default because ols")
    assert any("m1.ols" in n and "replaced by welch" in n for n in cfg.state.notes)
    assert any("Label ols" in n for n in cfg.state.notes)


async def test_missing_recode_fixture_counts_as_a_failed_attempt(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(**{"coder:m1.welch": ESTIMATE}))
    cfg = config(tmp_path, Recorder())
    coded = await code_plan(llm, make_plan(), smoke=cfg)
    assert coded.step("m1").default.id == "welch"
    assert "coder:m1.ols:recode" in [c.key for c in llm.calls]


async def test_all_options_failing_names_step_options_and_error(tmp_path: Path) -> None:
    llm = FakeLLM(scripted())
    with pytest.raises(LLMError) as raised:
        await code_plan(llm, make_plan(), smoke=config(tmp_path, Recorder()))
    message = str(raised.value)
    assert "step m1" in message
    assert "ols" in message and "welch" in message
    assert "no attribute norm" in message


class BudgetLLM(FakeLLM):
    async def complete(self, role, messages, *, key, **kwargs):
        if key.endswith(":recode"):
            raise BudgetExceeded("cap")
        return await super().complete(role, messages, key=key, **kwargs)


async def test_budget_exceeded_propagates_from_the_recode(tmp_path: Path) -> None:
    llm = BudgetLLM(scripted(**{"coder:m1.welch": ESTIMATE}))
    with pytest.raises(BudgetExceeded):
        await code_plan(llm, make_plan(), smoke=config(tmp_path, Recorder()))
