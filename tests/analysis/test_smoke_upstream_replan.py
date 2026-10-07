from __future__ import annotations

from pathlib import Path

import pytest

from borges.analysis.coder import code_plan
from borges.analysis.schemas import CoderOutput
from borges.llm.client import LLMError
from tests.analysis.fakes import FakeLLM, make_option
from tests.analysis.test_coder_smoke import Recorder, config, passing_guard
from tests.analysis.test_smoke_default_rescue import plan
from tests.analysis.test_smoke_upstream import MODEL

__all__ = ["passing_guard"]

CONSTANT = "def apply(df, ctx):\n    return df.assign(flag=0)"
ALSO_CONSTANT = "def apply(df, ctx):\n    return df.assign(flag=1)"
VARIES = "def apply(df, ctx):\n    return df.assign(flag=(df['outcome'] > 0).astype(int))"
BLAMES = MODEL.replace(
    "    cols =",
    "    if df['flag'].nunique() < 2:\n"
    "        raise ValueError('the exposure flag has the same value in every row: the earlier "
    "step that builds it produced a constant')\n    cols =",
)
REPLAN = "planner:replan:a1"


def planned(option_id: str, default: bool = False) -> dict:
    return {
        "id": option_id,
        "label": f"L {option_id}",
        "rationale": "r",
        "spec": f"build flag by {option_id}",
        "is_default": default,
    }


def constant_plan():
    built = plan()
    built.step("a1").options = [make_option("zero", True), make_option("one")]
    return built


def codes(**extra: str) -> dict:
    found = {"coder:a1.zero": CONSTANT, "coder:a1.one": ALSO_CONSTANT, "coder:m1.ols": BLAMES}
    return {key: CoderOutput(code=code) for key, code in {**found, **extra}.items()}


async def test_a_constant_input_is_replanned_at_the_step_that_builds_it(tmp_path: Path) -> None:
    responses = {**codes(**{"coder:a1.split": VARIES}), REPLAN: {"options": [planned("split")]}}
    llm = FakeLLM(responses)
    cfg = config(tmp_path, Recorder())
    coded = await code_plan(llm, constant_plan(), smoke=cfg)
    assert [o.id for o in coded.step("a1").options] == ["split"]
    assert coded.step("a1").default.id == "split"
    assert [o.id for o in coded.step("m1").options] == ["ols"]
    assert "planner:replan:m1" not in [c.key for c in llm.calls]
    asked = next(c for c in llm.calls if c.key == REPLAN).messages[-1]["content"]
    assert "produced a constant" in asked and "Rebuild the column" in asked
    assert any("re-planned 'a1' once and proposed: split" in n for n in cfg.state.notes)


async def test_a_replan_that_still_builds_a_constant_fails_with_the_model_reason(
    tmp_path: Path,
) -> None:
    responses = {**codes(**{"coder:a1.split": CONSTANT}), REPLAN: {"options": [planned("split")]}}
    llm = FakeLLM(responses)
    cfg = config(tmp_path, Recorder())
    with pytest.raises(LLMError, match="produced a constant"):
        await code_plan(llm, constant_plan(), smoke=cfg)
    keys = [c.key for c in llm.calls]
    assert keys.index(REPLAN) < keys.index("planner:replan:m1")
    assert not any("re-planned 'a1'" in n for n in cfg.state.notes)
