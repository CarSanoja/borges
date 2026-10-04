from __future__ import annotations

from pathlib import Path

from borges.analysis.coder import code_plan
from borges.analysis.models import AnalysisPlan, CodingSummary, Step
from borges.analysis.schemas import CoderOutput
from tests.analysis.fakes import FakeLLM, make_option, make_plan
from tests.analysis.test_coder_smoke import (
    Recorder,
    config,
    passing_guard,
)

__all__ = ["passing_guard"]

AGGREGATE = (
    "def apply(df, ctx):\n"
    '    out = df.groupby(df.index // 10).agg(outcome=("outcome", "min"))\n'
    '    out["outcome"] = out["outcome"].round(0)\n'
    '    return out.rename_axis("bucket").reset_index()'
)
NO_COVARIATES = "def apply(df, ctx):\n    ctx['covariates'] = []\n    return df.copy()"
NAMES_GROUP = "def apply(df, ctx):\n    ctx['covariates'] = ['group']\n    return df.copy()"
NAMES_OUTCOME = "def apply(df, ctx):\n    ctx['covariates'] = ['outcome']\n    return df.copy()"
MODEL = (
    "def estimate(df, ctx):\n"
    "    cols = list(ctx.get('covariates', []))\n"
    "    sub = df[list(dict.fromkeys(cols + ['outcome']))]\n"
    "    m = float(sub['outcome'].mean())\n"
    '    return {"estimate": m, "ci_low": m - 1.0, "ci_high": m + 1.0, "p_value": 0.5, '
    '"n": len(df)}'
)


def three_step_plan() -> AnalysisPlan:
    base = make_plan()
    return base.model_copy(
        update={
            "steps": [
                Step(
                    id="a1",
                    title="Aggregate",
                    kind="transform",
                    description="Aggregate",
                    options=[make_option("agg", True)],
                ),
                Step(
                    id="c1",
                    title="Covariates",
                    kind="feature",
                    description="Pick covariates",
                    options=[make_option("none", True), make_option("with_group")],
                ),
                Step(
                    id="m1",
                    title="Estimator",
                    kind="model",
                    description="Estimate",
                    options=[make_option("ols", True)],
                ),
            ]
        }
    )


def scripted(group_code: str = NAMES_GROUP, **extra: str) -> dict[str, CoderOutput]:
    base = {
        "coder:a1.agg": AGGREGATE,
        "coder:c1.none": NO_COVARIATES,
        "coder:c1.with_group": group_code,
        "coder:m1.ols": MODEL,
        **extra,
    }
    return {key: CoderOutput(code=code) for key, code in base.items()}


async def test_an_upstream_option_that_breaks_the_model_is_repaired(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(**{"coder:c1.with_group:smoke1": NAMES_OUTCOME}))
    recorder, summary = Recorder(), CodingSummary()
    cfg = config(tmp_path, recorder)
    coded = await code_plan(llm, three_step_plan(), smoke=cfg, summary=summary)
    step = coded.step("c1")
    assert step.option("with_group").code == NAMES_OUTCOME
    assert [o.option.id for o in cfg.state.outcomes["c1"]] == ["none", "with_group"]
    assert cfg.state.outcomes["c1"][1].option.code == NAMES_OUTCOME
    prompt = next(c for c in llm.calls if c.key == "coder:c1.with_group:smoke1")
    assert "KeyError" in prompt.messages[1]["content"]
    assert "model step" in prompt.messages[1]["content"]
    event = [e for e in recorder.events if e[0] == "c1" and e[1] == "with_group"][-1]
    assert event[2] == "repaired" and "caught upstream" in event[4]
    assert summary.failed == 0 and cfg.state.notes == []


async def test_an_upstream_option_whose_repair_still_breaks_the_model_is_dropped(
    tmp_path: Path,
) -> None:
    llm = FakeLLM(scripted(**{"coder:c1.with_group:smoke1": NAMES_GROUP}))
    recorder, summary = Recorder(), CodingSummary()
    cfg = config(tmp_path, recorder)
    coded = await code_plan(llm, three_step_plan(), smoke=cfg, summary=summary)
    assert [o.id for o in coded.step("c1").options] == ["none"]
    assert [o.option.id for o in cfg.state.outcomes["c1"]] == ["none"]
    assert len(cfg.state.notes) == 1
    note = cfg.state.notes[0]
    assert "The option 'Label with_group' of the step 'Covariates' was dropped" in note
    assert "KeyError" in note
    event = [e for e in recorder.events if e[0] == "c1" and e[1] == "with_group"][-1]
    assert event[2] == "failed"
    assert summary.failed == 1
    assert llm.keys().count("coder:c1.with_group:smoke1") == 1


async def test_working_alternatives_cost_no_probe_repair(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(group_code=NAMES_OUTCOME))
    cfg = config(tmp_path, Recorder())
    coded = await code_plan(llm, three_step_plan(), smoke=cfg)
    assert [o.id for o in coded.step("c1").options] == ["none", "with_group"]
    used = llm.keys()
    assert not [k for k in used if ":smoke" in k]
    assert cfg.state.notes == []
