from __future__ import annotations

import re
from pathlib import Path

import pytest

from borges.analysis.coder import code_plan
from borges.analysis.models import AnalysisPlan, CodingSummary, Step
from borges.analysis.schemas import CoderOutput
from borges.llm.client import LLMError
from tests.analysis.fakes import FakeLLM, make_option, make_plan
from tests.analysis.test_coder_smoke import Recorder, config, passing_guard
from tests.analysis.test_smoke_upstream_replan import BLAMES

__all__ = ["passing_guard"]

KEEPS_ONE_GROUP = (
    "def apply(df, ctx):\n"
    "    df = df.copy()\n"
    "    df['band'] = 'b'\n"
    "    df.loc[df['group'] == 'a', 'band'] = 'a'\n"
    "    return df[df['band'] != 'b']"
)
KEEPS_BOTH = "def apply(df, ctx):\n    return df[df['group'].isin(['a', 'b'])]"
FLAG = "def apply(df, ctx):\n    return df.assign(flag=(df['group'] == 'b').astype(int))"
SPLIT = "def apply(df, ctx):\n    return df.assign(flag=(df['outcome'] > 0).astype(int))"


def chain() -> AnalysisPlan:
    steps = [
        Step(
            id="f1",
            title="Window",
            kind="filter",
            description="Keep both groups",
            options=[make_option("both", True)],
        ),
        Step(
            id="a1",
            title="Flag",
            kind="transform",
            description="Build the flag",
            options=[make_option("group", True), make_option("split")],
            produces=["flag"],
        ),
        Step(
            id="m1",
            title="Estimator",
            kind="model",
            description="d",
            options=[make_option("ols", True)],
        ),
    ]
    return make_plan().model_copy(update={"steps": steps})


def codes(**extra: str) -> dict:
    found = {
        "coder:f1.both": KEEPS_ONE_GROUP,
        "coder:a1.group": FLAG,
        "coder:a1.split": SPLIT,
        "coder:m1.ols": BLAMES,
    }
    return {key: CoderOutput(code=code) for key, code in {**found, **extra}.items()}


async def test_a_constant_input_from_two_steps_up_is_repaired_at_the_filter(
    tmp_path: Path,
) -> None:
    """fertility_vote, 7 October: the filter kept only one group, the flag built from it was
    constant, and the re-plan went to the step just before the model."""
    llm = FakeLLM(codes(**{"coder:f1.both:smoke1": KEEPS_BOTH}))
    cfg, summary = config(tmp_path, Recorder()), CodingSummary()
    coded = await code_plan(llm, chain(), smoke=cfg, summary=summary)
    assert coded.step("f1").default.code == KEEPS_BOTH
    assert [o.id for o in coded.step("a1").options] == ["group", "split"]
    assert coded.step("a1").default.id == "group"
    assert [o.id for o in coded.step("m1").options] == ["ols"]
    asked = next(c for c in llm.calls if c.key == "coder:f1.both:smoke1").messages[-1]["content"]
    assert re.search(r"keeps \d+ of the 200 rows it receives", asked)
    assert "do not change what the spec does" in asked
    assert any("default of 'Window' was repaired" in n for n in cfg.state.notes)
    assert summary.repaired_after_smoke >= 1
    assert "planner:replan:m1" not in [c.key for c in llm.calls]


async def test_a_repair_that_still_leaves_a_constant_fails_as_before(tmp_path: Path) -> None:
    llm = FakeLLM(codes(**{"coder:f1.both:smoke1": KEEPS_ONE_GROUP}))
    cfg = config(tmp_path, Recorder())
    single = chain()
    single.step("a1").options = [make_option("group", True)]
    with pytest.raises(LLMError, match="produced a constant"):
        await code_plan(llm, single, smoke=cfg)
    assert not any("was repaired" in n for n in cfg.state.notes)
