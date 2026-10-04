from __future__ import annotations

from dataclasses import dataclass

import pytest

from borges.analysis import coder, coder_checks
from borges.analysis.schemas import CoderOutput
from borges.gateway.armor_hooks import ArmorBlocked
from borges.llm.client import LLMError, LLMResponse, Role
from tests.analysis.fakes import FakeLLM, make_plan
from tests.analysis.test_coder import guard

GOOD = "import numpy as np\n\n\ndef apply(df, ctx):\n    return df"


@dataclass
class ScreenedLLM(FakeLLM):
    refused: str = "coder.output carries code.dynamic"

    async def complete(self, role: Role, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        if kwargs["key"] == "coder:d1.keep":
            raise ArmorBlocked(self.refused, "coder")
        return await super().complete(role, messages, **kwargs)


@pytest.fixture(autouse=True)
def passing_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder_checks, "check_code", guard(set()))


async def test_code_refused_as_dynamic_is_written_again_with_the_reason() -> None:
    llm = ScreenedLLM({"coder:d1.keep:armor": CoderOutput(code=GOOD)})
    plan = make_plan()
    step = plan.step("d1")
    code, attempts, _ = await coder.generate_checked(llm, plan, step, step.option("keep"))
    assert code == GOOD and attempts == 2
    content = llm.calls[-1].messages[1]["content"]
    assert "coder.output carries code.dynamic" in content and "never call __import__" in content


async def test_any_other_refusal_still_fails_the_option() -> None:
    llm = ScreenedLLM({}, refused="coder.output carries injection.instruction")
    plan = make_plan()
    step = plan.step("d1")
    with pytest.raises(LLMError):
        await coder.generate_checked(llm, plan, step, step.option("keep"))
    assert llm.calls == []
