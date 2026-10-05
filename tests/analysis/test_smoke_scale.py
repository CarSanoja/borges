from __future__ import annotations

from pathlib import Path

from borges.analysis.coder import code_plan
from borges.analysis.models import CodingSummary
from borges.analysis.schemas import CoderOutput
from tests.analysis.fakes import FakeLLM, make_plan
from tests.analysis.test_coder_smoke import (
    ESTIMATE,
    KEEP,
    Recorder,
    config,
    passing_guard,
    responses,
)

__all__ = ["passing_guard"]

RAW = (
    "def estimate(df, ctx):\n"
    '    m = float(df["outcome"].mean())\n'
    '    return {"estimate": m + 5.0, "ci_low": m + 4.0, "ci_high": m + 6.0, "p_value": 0.5, '
    '"n": len(df)}'
)
FIXED = (
    "def estimate(df, ctx):\n"
    '    m = float(df["outcome"].mean())\n'
    '    return {"estimate": m, "ci_low": m - 1.0, "ci_high": m + 1.0, "p_value": 0.4, '
    '"n": len(df)}'
)
OTHER_SCALE = RAW.replace("m + 5.0", "m + 9.0").replace("m + 4.0", "m + 8.0")


def scripted(**overrides: str) -> dict[str, CoderOutput]:
    return responses(**{"coder:d1.trim": KEEP.replace("df.copy()", "df.head(100).copy()")}) | {
        key: CoderOutput(code=code) for key, code in {"coder:m1.welch": RAW, **overrides}.items()
    }


async def test_same_fit_on_different_scales_is_recoded_with_the_metric(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(**{"coder:m1.welch:scale": FIXED, "coder:m1.ols:scale": ESTIMATE}))
    summary = CodingSummary()
    cfg = config(tmp_path, Recorder())
    coded = await code_plan(llm, make_plan(), smoke=cfg, summary=summary)
    assert coded.step("m1").option("welch").code == FIXED
    text = next(c for c in llm.calls if c.key == "coder:m1.welch:scale").messages[-1]["content"]
    assert "mean_diff" in text and "Spec for welch on outcome" in text
    assert "Spec for ols on outcome" in text
    assert llm.keys().count("coder:m1.welch:scale") == 1
    assert summary.options_recoded_by_output_check == 1
    assert cfg.state.notes == []


async def test_a_persisting_scale_mismatch_adds_a_caveat_naming_both(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(**{"coder:m1.welch:scale": OTHER_SCALE, "coder:m1.ols:scale": ESTIMATE}))
    cfg = config(tmp_path, Recorder())
    await code_plan(llm, make_plan(), smoke=cfg)
    assert len(cfg.state.notes) == 1
    note = cfg.state.notes[0]
    assert "'Label ols'" in note and "'Label welch'" in note and "different scales" in note
    assert "mean_diff" in note


async def test_similar_estimates_are_not_a_scale_mismatch(tmp_path: Path) -> None:
    close = ESTIMATE.replace('float(df["outcome"].mean())', 'float(df["outcome"].mean()) * 1.001')
    llm = FakeLLM(scripted(**{"coder:m1.welch": close}))
    await code_plan(llm, make_plan(), smoke=config(tmp_path, Recorder()))
    used = llm.keys()
    assert not [k for k in used if k.endswith(":scale")]
