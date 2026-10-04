from __future__ import annotations

from pathlib import Path

from borges.analysis.coder import code_plan
from borges.analysis.models import AnalysisPlan, Step
from borges.analysis.schemas import CoderOutput
from tests.analysis.fakes import FakeLLM, make_option, make_plan
from tests.analysis.test_coder_smoke import Recorder, config, passing_guard
from tests.analysis.test_smoke_upstream import AGGREGATE, MODEL

__all__ = ["passing_guard"]

KEEPS = "def apply(df, ctx):\n    return df.copy()"
NEEDS_GROUP = MODEL.replace("    cols =", "    df['group'].nunique()\n    cols =")


def plan() -> AnalysisPlan:
    shape = Step(
        id="a1",
        title="Reshape",
        kind="transform",
        description="Aggregate",
        options=[make_option("agg", True), make_option("keep")],
    )
    model = Step(
        id="m1",
        title="Estimator",
        kind="model",
        description="d",
        options=[make_option("ols", True)],
    )
    return make_plan().model_copy(update={"steps": [shape, model]})


async def test_a_model_that_fails_after_the_default_runs_after_another_upstream_option(
    tmp_path: Path,
) -> None:
    codes = {"coder:a1.agg": AGGREGATE, "coder:a1.keep": KEEPS, "coder:m1.ols": NEEDS_GROUP}
    llm = FakeLLM({key: CoderOutput(code=code) for key, code in codes.items()})
    cfg = config(tmp_path, Recorder())
    coded = await code_plan(llm, plan(), smoke=cfg)
    assert coded.step("a1").default.id == "keep"
    assert [o.id for o in coded.step("m1").options] == ["ols"]
    assert cfg.state.defaults["a1"].option.id == "keep"
    assert any("'Label keep' became that step's default" in n for n in cfg.state.notes)
    used = llm.keys()
    assert not [k for k in used if "replan" in k]


async def test_a_model_no_option_of_the_previous_step_feeds_runs_without_that_step(
    tmp_path: Path,
) -> None:
    single = plan()
    single.step("a1").options = [make_option("agg", True)]
    codes = {"coder:a1.agg": AGGREGATE, "coder:m1.ols": NEEDS_GROUP}
    llm = FakeLLM({key: CoderOutput(code=code) for key, code in codes.items()})
    cfg = config(tmp_path, Recorder())
    coded = await code_plan(llm, single, smoke=cfg)
    assert [o.id for o in coded.step("a1").options] == ["left_out"]
    assert coded.step("a1").produces == []
    assert [o.id for o in coded.step("m1").options] == ["ols"]
    assert any("The decision 'Reshape' was left out" in n for n in cfg.state.notes)


async def test_a_fault_of_the_input_costs_no_repair_of_the_model(tmp_path: Path) -> None:
    constant = "def apply(df, ctx):\n    return df.assign(flag=0)"
    varies = "def apply(df, ctx):\n    return df.assign(flag=(df['outcome'] > 0).astype(int))"
    blames = MODEL.replace(
        "    cols =",
        "    if df['flag'].nunique() < 2:\n"
        "        raise ValueError('the exposure flag is constant: the earlier step that builds "
        "it produced a constant')\n    cols =",
    )
    built = plan()
    built.step("a1").options = [make_option("const", True), make_option("split")]
    codes = {"coder:a1.const": constant, "coder:a1.split": varies, "coder:m1.ols": blames}
    llm = FakeLLM({key: CoderOutput(code=code) for key, code in codes.items()})
    cfg = config(tmp_path, Recorder())
    coded = await code_plan(llm, built, smoke=cfg)
    assert coded.step("a1").default.id == "split"
    used = llm.keys()
    assert not [k for k in used if k.startswith("coder:m1.ols:smoke")]
