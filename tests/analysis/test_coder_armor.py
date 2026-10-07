from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from borges.analysis import coder, coder_checks
from borges.analysis.schemas import CoderOutput
from borges.gateway.armor_hooks import ArmorBlocked
from borges.llm.client import LLMError, LLMResponse, Role
from tests.analysis.fakes import Call, FakeLLM, make_plan
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
    assert "(code.dynamic)" in content and "never call __import__" in content


async def test_any_other_refusal_still_fails_the_option() -> None:
    llm = ScreenedLLM({}, refused="coder.output carries injection.instruction")
    plan = make_plan()
    step = plan.step("d1")
    with pytest.raises(LLMError):
        await coder.generate_checked(llm, plan, step, step.option("keep"))
    assert llm.calls == []


DUNDER = "coder.output carries code.dunder; obfuscation: leetspeak [__class__]"


@dataclass
class RefusingLLM(FakeLLM):
    refusals: dict[str, str] = field(default_factory=dict)

    async def complete(self, role: Role, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        reason = self.refusals.get(kwargs["key"])
        if reason is not None:
            self.calls.append(Call(role, messages, kwargs["key"], None, 0))
            raise ArmorBlocked(reason, role.value)
        return await super().complete(role, messages, **kwargs)


async def test_dunder_refusal_in_the_coder_path_is_asked_again_without_the_payload() -> None:
    llm = RefusingLLM(
        {"coder:d1.keep:armor": CoderOutput(code=GOOD)}, refusals={"coder:d1.keep": DUNDER}
    )
    plan = make_plan()
    step = plan.step("d1")
    code, attempts, _ = await coder.generate_checked(llm, plan, step, step.option("keep"))
    assert code == GOOD and attempts == 2
    content = llm.calls[-1].messages[1]["content"]
    assert "(code.dunder)" in content and "two underscores" in content
    assert "__class__" not in content and "leetspeak" not in content


async def test_dunder_refusal_in_the_repair_path_is_asked_again_once() -> None:
    llm = RefusingLLM(
        {"coder:d1.keep:smoke1:armor": CoderOutput(code=GOOD)},
        refusals={"coder:d1.keep:smoke1": DUNDER.replace("coder", "repairer")},
    )
    plan = make_plan()
    step = plan.step("d1")
    got = await coder._request_code(llm, plan, step, step.option("keep"), "boom", suffix=":smoke1")
    assert got == GOOD
    assert llm.keys() == ["coder:d1.keep:smoke1", "coder:d1.keep:smoke1:armor"]
    assert llm.calls[-1].role is Role.REPAIRER
    assert "__class__" not in llm.calls[-1].messages[1]["content"]


async def test_a_second_refusal_fails_the_option() -> None:
    llm = RefusingLLM(
        {}, refusals={"coder:d1.keep:smoke1": DUNDER, "coder:d1.keep:smoke1:armor": DUNDER}
    )
    plan = make_plan()
    step = plan.step("d1")
    with pytest.raises(ArmorBlocked):
        await coder._request_code(llm, plan, step, step.option("keep"), "boom", suffix=":smoke1")
    assert len(llm.calls) == 2


async def test_a_prompt_injection_refusal_in_the_repair_path_is_not_asked_again() -> None:
    llm = RefusingLLM(
        {}, refusals={"coder:d1.keep:smoke1": "repairer.output carries injection.instruction"}
    )
    plan = make_plan()
    step = plan.step("d1")
    with pytest.raises(ArmorBlocked):
        await coder._request_code(llm, plan, step, step.option("keep"), "boom", suffix=":smoke1")
    assert len(llm.calls) == 1
