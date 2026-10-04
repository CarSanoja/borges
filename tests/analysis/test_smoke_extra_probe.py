from __future__ import annotations

from pathlib import Path

from borges.analysis.coder import code_plan
from borges.analysis.smoke_extra import smoke_extra_option
from borges.llm.client import LLMError
from tests.analysis.fakes import FakeLLM, make_option
from tests.analysis.test_coder_smoke import Recorder, config, passing_guard
from tests.analysis.test_smoke_upstream import (
    NAMES_GROUP,
    NAMES_OUTCOME,
    scripted,
    three_step_plan,
)

__all__ = ["passing_guard"]


async def no_repair(*_: object) -> tuple[str, str | None, str]:
    raise LLMError("no repair")


async def smoked(tmp_path: Path):
    llm = FakeLLM(scripted(group_code=NAMES_OUTCOME))
    cfg = config(tmp_path, Recorder())
    plan = await code_plan(llm, three_step_plan(), smoke=cfg)
    return cfg, plan


async def test_an_adversary_option_that_breaks_the_model_is_refused(tmp_path: Path) -> None:
    cfg, plan = await smoked(tmp_path)
    option = make_option("adv_group", code=NAMES_GROUP)
    outcome = await smoke_extra_option(cfg, no_repair, plan.step("c1"), option, plan.steps)
    assert outcome is not None and outcome.status == "failed"
    assert outcome.error is not None and "was dropped" in outcome.error
    assert "KeyError" in outcome.error


async def test_an_adversary_option_the_model_can_use_is_kept(tmp_path: Path) -> None:
    cfg, plan = await smoked(tmp_path)
    code = "def apply(df, ctx):\n    ctx['covariates'] = []\n    return df.assign(extra=1.0)"
    option = make_option("adv_extra", code=code)
    outcome = await smoke_extra_option(cfg, no_repair, plan.step("c1"), option, plan.steps)
    assert outcome is not None and outcome.status != "failed"


async def test_a_repair_through_the_probe_replaces_the_adversary_code(tmp_path: Path) -> None:
    cfg, plan = await smoked(tmp_path)
    fixed = NAMES_OUTCOME.replace("df.copy()", "df.copy().assign(flag=1)")

    async def repair(*_: object) -> tuple[str, str | None, str]:
        return fixed, None, "model"

    option = make_option("adv_group", code=NAMES_GROUP)
    outcome = await smoke_extra_option(cfg, repair, plan.step("c1"), option, plan.steps)
    assert outcome is not None and outcome.status == "repaired"
    assert outcome.option.code == fixed
