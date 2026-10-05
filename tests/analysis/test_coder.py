from __future__ import annotations

import pytest

from borges.analysis import coder, coder_checks
from borges.analysis.coder import _request_code, code_option, code_plan, repair_option
from borges.analysis.schemas import CoderOutput
from borges.llm.client import LLMError, Role
from tests.analysis.fakes import FakeLLM, make_plan

GOOD = "def apply(df, ctx):\n    return df"


def guard(bad: set[str]):
    def check(code: str, kind: str, intent: str = "") -> list[str]:
        return [f"bad: {code}"] if code in bad else []

    return check


@pytest.fixture(autouse=True)
def passing_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder_checks, "check_code", guard(set()))


async def test_code_option_key_and_prompt() -> None:
    llm = FakeLLM({"coder:m1.welch": CoderOutput(code="X")})
    plan = make_plan()
    step = plan.step("m1")
    assert await code_option(llm, plan, step, step.option("welch")) == "X"
    call = llm.calls[0]
    assert call.role is Role.CODER and call.max_tokens == 2500 and call.schema is CoderOutput
    content = call.messages[1]["content"]
    assert "outcome" in content and "float64" in content
    assert "Spec for keep on outcome" in content and "Spec for trim on outcome" in content
    assert "estimate(df, ctx)" in content
    assert (
        "def estimate" in call.messages[0]["content"] or "estimate" in call.messages[0]["content"]
    )


async def test_code_option_repair_includes_previous_code_and_error() -> None:
    llm = FakeLLM({"coder:d1.trim:repair": CoderOutput(code="Y")})
    plan = make_plan()
    step = plan.step("d1")
    option = step.option("trim").model_copy(update={"code": "OLD CODE"})
    assert await _request_code(llm, plan, step, option, error="boom") == "Y"
    assert llm.keys() == ["coder:d1.trim:repair"]
    content = llm.calls[0].messages[1]["content"]
    assert "OLD CODE" in content and "boom" in content
    assert "Spec for keep on outcome" not in content


async def test_code_plan_codes_missing_only_and_reports() -> None:
    llm = FakeLLM(
        {
            "coder:d1.trim": CoderOutput(code="T"),
            "coder:m1.welch": CoderOutput(code="W"),
        }
    )
    plan = make_plan(with_code=True)
    events: list[tuple[str, str, bool, int, str | None]] = []

    async def on_coded(
        step_id: str, option_id: str, ok: bool, attempts: int, err: str | None, models: list[str]
    ) -> None:
        events.append((step_id, option_id, ok, attempts, err))

    coded = await code_plan(llm, plan, on_coded=on_coded)
    assert sorted(llm.keys()) == ["coder:d1.trim", "coder:m1.welch"]
    assert coded.step("d1").option("trim").code == "T"
    assert coded.step("m1").option("welch").code == "W"
    assert plan.step("d1").option("trim").code is None
    assert sorted(events) == [("d1", "trim", True, 1, None), ("m1", "welch", True, 1, None)]


async def test_code_plan_repairs_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder_checks, "check_code", guard({"BAD"}))
    llm = FakeLLM(
        {
            "coder:d1.trim": CoderOutput(code="BAD"),
            "coder:d1.trim:repair": CoderOutput(code="FIXED"),
            "coder:m1.welch": CoderOutput(code="W"),
        }
    )
    events: list[tuple[str, str, bool, int, str | None]] = []

    async def on_coded(*args) -> None:
        events.append(args[:5])

    coded = await code_plan(llm, make_plan(with_code=True), on_coded=on_coded)
    assert coded.step("d1").option("trim").code == "FIXED"
    assert "bad: BAD" in llm.calls[1].messages[1]["content"] or any(
        "bad: BAD" in c.messages[1]["content"] for c in llm.calls
    )
    assert ("d1", "trim", True, 2, None) in events


async def test_code_plan_drops_failing_non_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder_checks, "check_code", guard({"BAD"}))
    llm = FakeLLM(
        {
            "coder:d1.trim": CoderOutput(code="BAD"),
            "coder:d1.trim:repair": CoderOutput(code="BAD"),
            "coder:m1.welch": CoderOutput(code="W"),
        }
    )
    events: list[tuple[str, str, bool, int, str | None]] = []

    async def on_coded(*args) -> None:
        events.append(args)

    coded = await code_plan(llm, make_plan(with_code=True), on_coded=on_coded)
    assert [o.id for o in coded.step("d1").options] == ["keep"]
    failed = [e for e in events if e[1] == "trim"][0]
    assert failed[2] is False and failed[3] == 2 and "bad: BAD" in failed[4]


async def test_code_plan_promotes_coded_sibling_when_default_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(coder_checks, "check_code", guard({"BAD"}))
    plan = make_plan()
    llm = FakeLLM(
        {
            "coder:d1.keep": CoderOutput(code="BAD"),
            "coder:d1.keep:repair": CoderOutput(code="BAD"),
            "coder:d1.trim": CoderOutput(code="T"),
            "coder:m1.ols": CoderOutput(code="O"),
            "coder:m1.welch": CoderOutput(code="W"),
        }
    )
    events: list[tuple[str, str, bool, int, str | None]] = []

    async def on_coded(*args) -> None:
        events.append(args)

    coded = await code_plan(llm, plan, on_coded=on_coded)
    step = coded.step("d1")
    assert [o.id for o in step.options] == ["trim"]
    assert step.options[0].is_default is True
    promoted = [e for e in events if e[1] == "trim" and e[4]]
    assert promoted and "promoted to default" in promoted[0][4] and "keep" in promoted[0][4]


async def test_code_plan_raises_when_no_option_of_step_codes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(coder_checks, "check_code", guard({"BAD"}))
    llm = FakeLLM(
        {
            "coder:d1.keep": CoderOutput(code="BAD"),
            "coder:d1.keep:repair": CoderOutput(code="BAD"),
            "coder:d1.trim": CoderOutput(code="BAD"),
            "coder:d1.trim:repair": CoderOutput(code="BAD"),
            "coder:m1.ols": CoderOutput(code="O"),
            "coder:m1.welch": CoderOutput(code="W"),
        }
    )
    with pytest.raises(LLMError, match="d1.keep"):
        await code_plan(llm, make_plan())


async def test_repair_option_returns_checked_option(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = FakeLLM({"coder:d1.trim:repair": CoderOutput(code="FIXED")})
    plan = make_plan()
    step = plan.step("d1")
    option = step.option("trim").model_copy(update={"code": "OLD"})
    repaired = await repair_option(llm, plan, step, option, "err")
    assert repaired.code == "FIXED" and repaired.id == "trim"
    assert option.code == "OLD"

    monkeypatch.setattr(coder_checks, "check_code", guard({"FIXED"}))
    with pytest.raises(LLMError):
        await repair_option(llm, plan, step, option, "err")


async def test_code_option_rejects_code_that_violates_the_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(coder_checks, "check_code", guard({"BAD", "WORSE"}))
    llm = FakeLLM(
        {
            "coder:m1.welch": CoderOutput(code="BAD"),
            "coder:m1.welch:repair": CoderOutput(code="WORSE"),
            "coder:m1.welch:guard_recode": CoderOutput(code="WORSE"),
        }
    )
    plan = make_plan()
    step = plan.step("m1")
    with pytest.raises(LLMError, match="violates the guard"):
        await code_option(llm, plan, step, step.option("welch"))
    assert llm.keys() == ["coder:m1.welch", "coder:m1.welch:repair", "coder:m1.welch:guard_recode"]


async def test_code_option_repairs_guard_violation_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder_checks, "check_code", guard({"BAD"}))
    llm = FakeLLM(
        {
            "coder:m1.welch": CoderOutput(code="BAD"),
            "coder:m1.welch:repair": CoderOutput(code="OK"),
        }
    )
    plan = make_plan()
    step = plan.step("m1")
    assert await code_option(llm, plan, step, step.option("welch")) == "OK"


async def test_a_fresh_recode_follows_a_failed_guard_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    monkeypatch.setattr(coder_checks, "check_code", guard({"BAD", "WORSE"}))
    monkeypatch.setattr(coder_checks, "check_code", guard({"BAD", "WORSE"}))
    llm = FakeLLM(
        {
            "coder:m1.welch": CoderOutput(code="BAD"),
            "coder:m1.welch:repair": CoderOutput(code="WORSE"),
            "coder:m1.welch:guard_recode": CoderOutput(code="OK"),
        }
    )
    plan = make_plan()
    step = plan.step("m1")
    code, attempts, _ = await coder.generate_checked(llm, plan, step, step.option("welch"))
    assert attempts == 3 and code is not None


async def test_a_step_none_of_whose_options_codes_is_replanned_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(coder_checks, "check_code", guard({"BAD"}))
    fresh = {"id": "fresh", "label": "Fresh", "rationale": "r", "spec": "keep all rows"}
    llm = FakeLLM(
        {
            "coder:d1.keep": CoderOutput(code="BAD"),
            "coder:d1.keep:repair": CoderOutput(code="BAD"),
            "coder:d1.trim": CoderOutput(code="BAD"),
            "coder:d1.trim:repair": CoderOutput(code="BAD"),
            "planner:replan:d1": {"options": [{**fresh, "is_default": True}]},
            "coder:d1.fresh": CoderOutput(code=GOOD),
            "coder:m1.ols": CoderOutput(code="O"),
            "coder:m1.welch": CoderOutput(code="W"),
        }
    )
    coded = await code_plan(llm, make_plan())
    step = coded.step("d1")
    assert [o.id for o in step.options] == ["fresh"]
    assert step.default.id == "fresh" and step.default.code == GOOD
