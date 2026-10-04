from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis import coder_checks
from borges.analysis.coder import code_plan
from borges.analysis.coder_smoke import SmokeConfig, sample_rows
from borges.analysis.models import CodingSummary
from borges.analysis.schemas import CoderOutput
from borges.sandbox.local_backend import LocalBackend
from tests.analysis.fakes import FakeLLM, make_plan

KEEP = "def apply(df, ctx):\n    return df.copy()"
TRIM_RAISES = 'def apply(df, ctx):\n    return df[df["missing_col"] > 0]'
TRIM_FIXED = 'def apply(df, ctx):\n    return df[df["outcome"].notna()]'
ESTIMATE = (
    "def estimate(df, ctx):\n"
    '    m = float(df["outcome"].mean())\n'
    '    return {"estimate": m, "ci_low": m - 1.0, "ci_high": m + 1.0, "p_value": 0.5, '
    '"n": len(df)}'
)
BAD_ESTIMATE = (
    "def estimate(df, ctx):\n"
    '    return {"estimate": 1.0, "ci_low": 2.0, "ci_high": 1.0, "p_value": 0.5, "n": 3}'
)


real_check = coder_checks.check_code


@pytest.fixture(autouse=True)
def passing_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder_checks, "check_code", lambda code, kind, intent="": [])


def dataset(rows: int = 300) -> bytes:
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"group": ["a", "b"] * (rows // 2), "outcome": rng.normal(size=rows)})
    buffer = io.BytesIO()
    frame.to_parquet(buffer)
    return buffer.getvalue()


def responses(**overrides: str) -> dict[str, CoderOutput]:
    base = {
        "coder:d1.keep": KEEP,
        "coder:d1.trim": TRIM_FIXED,
        "coder:m1.ols": ESTIMATE,
        "coder:m1.welch": ESTIMATE,
    }
    return {key: CoderOutput(code=code) for key, code in {**base, **overrides}.items()}


class Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, str, int, str | None]] = []

    async def __call__(self, *args) -> None:
        self.events.append(args)

    def status(self, option_id: str) -> tuple[str, int, str | None]:
        found = next(e for e in self.events if e[1] == option_id)
        return found[2], found[3], found[4]


def config(tmp_path: Path, recorder: Recorder, rows: int = 300) -> SmokeConfig:
    return SmokeConfig(LocalBackend(tmp_path), dataset(rows), recorder)


async def test_passing_options_cost_no_extra_llm_calls(tmp_path: Path) -> None:
    distinct = responses(
        **{
            "coder:d1.trim": "def apply(df, ctx):\n    return df.head(100).copy()",
            "coder:m1.welch": ESTIMATE.replace("0.5", "0.2"),
        }
    )
    llm = FakeLLM(distinct)
    recorder, summary = Recorder(), CodingSummary()
    coded = await code_plan(llm, make_plan(), smoke=config(tmp_path, recorder), summary=summary)
    assert sorted(llm.keys()) == sorted(distinct)
    assert {e[2] for e in recorder.events} == {"passed"} and len(recorder.events) == 4
    assert [o.id for o in coded.step("d1").options] == ["keep", "trim"]
    assert summary == CodingSummary(options=4, smoke_tested=4, repaired_after_smoke=0, failed=0)


async def test_runtime_error_is_sent_back_and_the_repair_is_kept(tmp_path: Path) -> None:
    llm = FakeLLM(responses(**{"coder:d1.trim": TRIM_RAISES, "coder:d1.trim:smoke1": TRIM_FIXED}))
    recorder, summary = Recorder(), CodingSummary()
    coded = await code_plan(llm, make_plan(), smoke=config(tmp_path, recorder), summary=summary)
    assert coded.step("d1").option("trim").code == TRIM_FIXED
    assert recorder.status("trim") == ("repaired", 2, None)
    repair_call = next(c for c in llm.calls if c.key == "coder:d1.trim:smoke1")
    prompt = repair_call.messages[1]["content"]
    assert "KeyError" in prompt and "missing_col" in prompt and TRIM_RAISES in prompt
    assert str(tmp_path) not in prompt
    assert summary == CodingSummary(options=4, smoke_tested=4, repaired_after_smoke=1, failed=0)


async def test_option_is_dropped_when_repairs_run_out(tmp_path: Path) -> None:
    llm = FakeLLM(
        responses(
            **{
                "coder:d1.trim": TRIM_RAISES,
                "coder:d1.trim:smoke1": TRIM_RAISES,
                "coder:d1.trim:smoke2": TRIM_RAISES,
            }
        )
    )
    recorder, summary = Recorder(), CodingSummary()
    coded = await code_plan(llm, make_plan(), smoke=config(tmp_path, recorder), summary=summary)
    assert [o.id for o in coded.step("d1").options] == ["keep"]
    status, attempts, error = recorder.status("trim")
    assert status == "failed" and attempts == 3 and "KeyError" in (error or "")
    assert llm.keys().count("coder:d1.trim:smoke1") == 1
    assert not any(c.key.endswith("smoke3") for c in llm.calls)
    assert summary.failed == 1 and summary.repaired_after_smoke == 0


async def test_invalid_estimate_result_triggers_a_repair(tmp_path: Path) -> None:
    llm = FakeLLM(responses(**{"coder:m1.welch": BAD_ESTIMATE, "coder:m1.welch:smoke1": ESTIMATE}))
    recorder = Recorder()
    await code_plan(llm, make_plan(), smoke=config(tmp_path, recorder))
    assert recorder.status("welch") == ("repaired", 2, None)
    prompt = next(c for c in llm.calls if c.key == "coder:m1.welch:smoke1").messages[1]["content"]
    assert "is inverted" in prompt


async def test_failing_default_promotes_a_smoked_sibling(tmp_path: Path) -> None:
    llm = FakeLLM(
        responses(
            **{
                "coder:d1.keep": TRIM_RAISES,
                "coder:d1.keep:smoke1": TRIM_RAISES,
                "coder:d1.keep:smoke2": TRIM_RAISES,
            }
        )
    )
    recorder = Recorder()
    coded = await code_plan(llm, make_plan(), smoke=config(tmp_path, recorder))
    step = coded.step("d1")
    assert [o.id for o in step.options] == ["trim"] and step.options[0].is_default
    assert recorder.status("keep")[0] == "failed"


async def test_a_data_step_with_no_runnable_option_is_left_out_and_reported(
    tmp_path: Path,
) -> None:
    llm = FakeLLM(
        responses(
            **{
                "coder:d1.keep": TRIM_RAISES,
                "coder:d1.keep:smoke1": TRIM_RAISES,
                "coder:d1.keep:smoke2": TRIM_RAISES,
                "coder:d1.trim": TRIM_RAISES,
                "coder:d1.trim:smoke1": TRIM_RAISES,
                "coder:d1.trim:smoke2": TRIM_RAISES,
            }
        )
    )
    cfg = config(tmp_path, Recorder())
    coded = await code_plan(llm, make_plan(), smoke=cfg)
    assert [o.id for o in coded.step("d1").options] == ["left_out"]
    assert [o.id for o in coded.step("m1").options] == ["ols", "welch"]
    left = [n for n in cfg.state.notes if "was left out of the analysis" in n]
    assert len(left) == 1 and "The decision 'Outliers'" in left[0]
    assert "Label keep, Label trim" in left[0] and "does not reflect that decision" in left[0]


async def test_smoke_runs_each_option_after_the_default_prefix(tmp_path: Path) -> None:
    rename = "def apply(df, ctx):\n    return df.assign(extra=1.0)"
    needs_extra = (
        "def estimate(df, ctx):\n"
        '    m = float(df["extra"].mean())\n'
        '    return {"estimate": m, "ci_low": m - 1.0, "ci_high": m + 1.0, "p_value": 0.5, '
        '"n": len(df)}'
    )
    llm = FakeLLM(responses(**{"coder:d1.keep": rename, "coder:m1.ols": needs_extra}))
    recorder = Recorder()
    await code_plan(llm, make_plan(), smoke=config(tmp_path, recorder))
    assert recorder.status("ols") == ("passed", 1, None)


def test_sample_is_small_deterministic_and_capped() -> None:
    small = dataset(100)
    assert sample_rows(small) == small
    mid = pd.read_parquet(io.BytesIO(sample_rows(dataset(10_000))))
    assert len(mid) == 500
    big = pd.read_parquet(io.BytesIO(sample_rows(dataset(100_000))))
    assert len(big) == 2000
    assert sample_rows(dataset(10_000)) == sample_rows(dataset(10_000))


async def test_syntax_error_repair_goes_through_the_guard_and_is_resent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = "def apply(df, ctx):\n    return (df\n"
    llm = FakeLLM(
        responses(
            **{
                "coder:d1.trim": TRIM_RAISES,
                "coder:d1.trim:smoke1": broken,
                "coder:d1.trim:smoke2": TRIM_FIXED,
            }
        )
    )
    recorder = Recorder()
    monkeypatch.setattr(coder_checks, "check_code", real_check)
    coded = await code_plan(llm, make_plan(), smoke=config(tmp_path, recorder))
    assert coded.step("d1").option("trim").code == TRIM_FIXED
    prompt = next(c for c in llm.calls if c.key == "coder:d1.trim:smoke2").messages[1]["content"]
    assert "syntax error at line" in prompt and "return (df" in prompt


async def test_promotion_after_smoke_failure_is_reported(tmp_path: Path) -> None:
    llm = FakeLLM(
        responses(
            **{
                "coder:d1.keep": TRIM_RAISES,
                "coder:d1.keep:smoke1": TRIM_RAISES,
                "coder:d1.keep:smoke2": TRIM_RAISES,
            }
        )
    )
    recorder = Recorder()
    await code_plan(llm, make_plan(), smoke=config(tmp_path, recorder))
    notes = [e for e in recorder.events if e[1] == "trim" and e[4]]
    assert notes and "promoted to default because keep" in notes[0][4]
