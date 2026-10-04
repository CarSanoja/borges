from __future__ import annotations

from typing import cast

import pytest

from borges.analysis.smoke_replan import both_rounds_message, has_survivor, replan_outcomes
from borges.analysis.smoke_types import Outcome, Replanned, SmokeConfig
from borges.llm.client import LLMError
from borges.sandbox.backend import BranchBackend
from tests.analysis.fakes import make_option, make_plan


def outcome(option_id: str, status: str = "failed", error: str | None = "boom") -> Outcome:
    return Outcome(make_option(option_id), status, 1, error, None, [])


def config() -> SmokeConfig:
    return SmokeConfig(cast(BranchBackend, None), b"")


def test_has_survivor_needs_one_option_that_did_not_fail() -> None:
    assert not has_survivor([])
    assert not has_survivor([outcome("a")])
    assert has_survivor([outcome("a"), outcome("b", "repaired", None)])


def test_the_message_names_both_rounds_and_every_option() -> None:
    step = make_plan().step("m1")
    text = both_rounds_message(
        step,
        [outcome("a", error="first error"), outcome("b")],
        [outcome("c", error="second error")],
        Replanned([], {"d": "not coded: guard"}),
    )
    assert "step m1" in text and "re-plan" in text
    assert "options tried: a, b; last error: first error" in text
    assert "options tried: c, d; last error: second error" in text


async def test_nothing_changes_when_the_planner_has_no_reply() -> None:
    step = make_plan().step("m1")
    first = [outcome("ols")]

    async def replan(*_):
        return None

    async def again() -> list[Outcome]:
        raise AssertionError("must not run")

    cfg = config()
    assert await replan_outcomes(cfg, replan, step, first, again) is first
    assert cfg.state.notes == []


async def test_new_options_are_announced_and_replace_the_step_options() -> None:
    step = make_plan().step("m1")
    announced: list[tuple] = []

    async def on_replan(*args) -> None:
        announced.append(args)

    async def replan(*_):
        return Replanned([make_option("fresh", True, "code")])

    async def again() -> list[Outcome]:
        return [outcome("fresh", "passed", None)]

    cfg = config()
    cfg.on_replan = on_replan
    result = await replan_outcomes(cfg, replan, step, [outcome("ols"), outcome("welch")], again)
    assert result[0].option.id == "fresh" and [o.id for o in step.options] == ["fresh"]
    assert announced == [("m1", ["ols", "welch"], ["fresh"])]
    assert "fresh" in cfg.state.notes[0] and "ols, welch" in cfg.state.notes[0]


async def test_a_second_failed_round_raises_with_both_rounds() -> None:
    step = make_plan().step("m1")

    async def replan(*_):
        return Replanned([make_option("fresh", True, "code")])

    async def again() -> list[Outcome]:
        return [outcome("fresh", error="still broken")]

    with pytest.raises(LLMError, match="re-plan") as caught:
        await replan_outcomes(config(), replan, step, [outcome("ols")], again)
    assert "ols" in str(caught.value) and "still broken" in str(caught.value)


async def test_a_replan_with_no_codable_option_raises_without_a_second_smoke() -> None:
    step = make_plan().step("m1")

    async def replan(*_):
        return Replanned([], {"fresh": "guard violation"})

    async def again() -> list[Outcome]:
        raise AssertionError("must not run")

    with pytest.raises(LLMError, match="guard violation"):
        await replan_outcomes(config(), replan, step, [outcome("ols")], again)
