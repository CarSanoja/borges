from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from borges.analysis import coder
from borges.analysis.coder import code_plan
from borges.analysis.coder_smoke import SmokeConfig
from borges.analysis.models import CodingSummary
from borges.analysis.schemas import CoderOutput
from borges.llm.client import LLMError
from borges.sandbox.local_backend import LocalBackend
from tests.analysis.fakes import FakeLLM, make_plan

GOOD = (
    "def estimate(df, ctx):\n"
    '    m = float(df["outcome"].mean())\n'
    '    return {"estimate": m, "ci_low": m - 1.0, "ci_high": m + 1.0, "p_value": 0.5, '
    '"n": len(df)}'
)
BROKEN = (
    "def estimate(df, ctx):\n"
    '    m = float(df["no_such_column"].mean())\n'
    '    return {"estimate": m, "ci_low": m - 1.0, "ci_high": m + 1.0, "p_value": 0.5, '
    '"n": len(df)}'
)
APPLY = "def apply(df, ctx):\n    return df.copy()"
REPLAN = "planner:replan:m1"


@pytest.fixture(autouse=True)
def passing_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder, "check_code", lambda code, kind, intent="": [])


def dataset() -> bytes:
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"group": ["a", "b"] * 150, "outcome": rng.normal(size=300)})
    buffer = io.BytesIO()
    frame.to_parquet(buffer)
    return buffer.getvalue()


def planned(option_id: str, default: bool = False) -> dict[str, Any]:
    return {
        "id": option_id,
        "label": f"L {option_id}",
        "rationale": "r",
        "spec": f"fit {option_id} on outcome",
        "is_default": default,
    }


def code(text: str) -> CoderOutput:
    return CoderOutput(code=text)


def scripted(**extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "coder:d1.keep": code(APPLY),
        "coder:d1.trim": code(APPLY),
        "coder:m1.ols": code(BROKEN),
        "coder:m1.welch": code(BROKEN),
    }
    for option in ("ols", "welch"):
        for attempt in (1, 2):
            base[f"coder:m1.{option}:smoke{attempt}"] = code(BROKEN)
    return {**base, **extra}


class Log:
    def __init__(self) -> None:
        self.replans: list[tuple] = []
        self.coded: list[tuple] = []

    async def on_replan(self, *args: Any) -> None:
        self.replans.append(args)

    async def on_coded(self, *args: Any) -> None:
        self.coded.append(args)


def config(tmp_path: Path, log: Log) -> SmokeConfig:
    smoke = SmokeConfig(LocalBackend(tmp_path), dataset())
    smoke.on_replan = log.on_replan
    return smoke


async def test_a_step_that_loses_every_option_is_replanned_once_and_the_run_continues(
    tmp_path: Path,
) -> None:
    llm = FakeLLM(
        scripted(
            **{
                REPLAN: {"options": [planned("ols", True), planned("robust")]},
                "coder:m1.ols_2": code(GOOD),
                "coder:m1.robust": code(GOOD),
            }
        )
    )
    log, summary = Log(), CodingSummary()
    coded = await code_plan(
        llm,
        make_plan(),
        log.on_coded,
        smoke=config(tmp_path, log),
        summary=summary,
    )
    step = coded.step("m1")
    assert [o.id for o in step.options] == ["ols_2", "robust"] and step.default.id == "ols_2"
    assert all(o.code == GOOD for o in step.options)
    assert log.replans == [("m1", ["ols", "welch"], ["ols_2", "robust"])]
    assert llm.keys().count(REPLAN) == 1
    assert ("m1", "robust", True, 1, None, ["fake"]) in log.coded
    assert summary.options == 6 and summary.failed >= 2
    prompt = next(c for c in llm.calls if c.key == REPLAN).messages[1]["content"]
    assert "no_such_column" in prompt and '"n_unique":2' in prompt


async def test_the_untouched_steps_are_not_replanned(tmp_path: Path) -> None:
    llm = FakeLLM(
        scripted(
            **{
                REPLAN: {"options": [planned("fresh", True)]},
                "coder:m1.fresh": code(GOOD),
            }
        )
    )
    coded = await code_plan(llm, make_plan(), smoke=config(tmp_path, Log()))
    assert [o.id for o in coded.step("d1").options] == ["keep", "trim"]
    assert "planner:replan:d1" not in [c.key for c in llm.calls]


async def test_when_the_replacements_also_fail_the_error_names_both_rounds(tmp_path: Path) -> None:
    llm = FakeLLM(
        scripted(
            **{
                REPLAN: {"options": [planned("fresh", True)]},
                "coder:m1.fresh": code(BROKEN),
                "coder:m1.fresh:smoke1": code(BROKEN),
                "coder:m1.fresh:smoke2": code(BROKEN),
            }
        )
    )
    log = Log()
    with pytest.raises(LLMError) as caught:
        await code_plan(llm, make_plan(), smoke=config(tmp_path, log))
    text = str(caught.value)
    assert "re-plan" in text and "options tried: ols, welch" in text
    assert "options tried: fresh" in text and "no_such_column" in text
    assert log.replans == [("m1", ["ols", "welch"], ["fresh"])]
    assert llm.keys().count(REPLAN) == 1


async def test_a_missing_replan_key_fails_exactly_as_before(tmp_path: Path) -> None:
    llm = FakeLLM(scripted())
    log = Log()
    with pytest.raises(LLMError, match="no option passed its smoke run") as caught:
        await code_plan(llm, make_plan(), smoke=config(tmp_path, log))
    assert "re-plan" not in str(caught.value) and log.replans == []


async def test_an_unusable_replan_reply_fails_as_before(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(**{REPLAN: {"options": []}}))
    with pytest.raises(LLMError, match="no option passed its smoke run") as caught:
        await code_plan(llm, make_plan(), smoke=config(tmp_path, Log()))
    assert "re-plan" not in str(caught.value)


async def test_options_that_cannot_be_coded_are_dropped_from_the_replan(tmp_path: Path) -> None:
    llm = FakeLLM(
        scripted(
            **{
                REPLAN: {"options": [planned("lost", True), planned("kept")]},
                "coder:m1.kept": code(GOOD),
            }
        )
    )
    log = Log()
    coded = await code_plan(llm, make_plan(), log.on_coded, smoke=config(tmp_path, log))
    step = coded.step("m1")
    assert [o.id for o in step.options] == ["kept"] and step.options[0].is_default
    assert log.replans == [("m1", ["ols", "welch"], ["kept"])]
    assert any(e[1] == "lost" and e[2] is False for e in log.coded)
