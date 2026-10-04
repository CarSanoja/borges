from __future__ import annotations

from pathlib import Path

import pytest

from borges.analysis.coder import code_plan
from borges.analysis.models import Option
from borges.analysis.smoke_extra import smoke_extra_option
from borges.llm.client import LLMError
from tests.analysis.fakes import FakeLLM, make_option, make_plan
from tests.analysis.test_coder_smoke import Recorder, config, passing_guard
from tests.analysis.test_smoke_collision import HEAD, SHIFTED, scripted

__all__ = ["passing_guard"]


async def no_repair(*_: object) -> tuple[str, str | None, str]:
    raise LLMError("no repair")


async def smoked(tmp_path: Path, llm: FakeLLM):
    cfg = config(tmp_path, Recorder())
    plan = await code_plan(llm, make_plan(), smoke=cfg)
    return cfg, plan


def adversary(option_id: str, code: str) -> Option:
    return make_option(option_id, code=code)


@pytest.mark.parametrize("step_id", ["d1", "m1"])
async def test_an_adversary_option_colliding_with_a_planner_option_is_recoded(
    tmp_path: Path, step_id: str
) -> None:
    keep_code = scripted()["coder:d1.keep"].code
    estimate = scripted()["coder:m1.ols"].code
    fixed = HEAD.replace("100", "50") if step_id == "d1" else SHIFTED.replace("0.2", "0.1")
    llm = FakeLLM(
        scripted(
            **{
                "coder:d1.trim": HEAD,
                "coder:m1.welch": SHIFTED,
                "coder:d1.adv_dup:collision": fixed,
                "coder:m1.adv_dup:collision": fixed,
            }
        )
    )
    cfg, plan = await smoked(tmp_path, llm)
    base = keep_code if step_id == "d1" else estimate
    outcome = await smoke_extra_option(
        cfg, no_repair, plan.step(step_id), adversary("adv_dup", base)
    )
    assert outcome is not None and outcome.option.code == fixed
    assert llm.keys().count(f"coder:{step_id}.adv_dup:collision") == 1
    assert cfg.state.notes == []


async def test_an_adversary_collision_that_persists_is_noted(tmp_path: Path) -> None:
    keep_code = scripted()["coder:d1.keep"].code
    llm = FakeLLM(
        scripted(
            **{
                "coder:d1.trim": HEAD,
                "coder:m1.welch": SHIFTED,
                "coder:d1.adv_dup:collision": keep_code,
            }
        )
    )
    cfg, plan = await smoked(tmp_path, llm)
    outcome = await smoke_extra_option(
        cfg, no_repair, plan.step("d1"), adversary("adv_dup", keep_code)
    )
    assert outcome is not None and outcome.status != "failed"
    assert len(cfg.state.notes) == 1 and "d1.adv_dup" in cfg.state.notes[0]
