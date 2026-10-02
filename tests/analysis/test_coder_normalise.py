from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from borges.analysis import coder
from borges.analysis.coder import code_plan
from borges.analysis.coder_normalise import strip_trailing_closer
from borges.analysis.schemas import CoderOutput
from tests.analysis.fakes import FakeLLM, make_plan

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.mark.parametrize("name", ["stray_brace_religiosity_ols", "stray_brace_religiosity_bayes"])
def test_real_samples_lose_only_the_stray_brace(name: str) -> None:
    code = json.loads((FIXTURES / f"{name}.json").read_text())["code"]
    with pytest.raises(SyntaxError):
        ast.parse(code)
    fixed, normalised = strip_trailing_closer(code)
    assert normalised
    ast.parse(fixed)
    assert fixed.rstrip().endswith("}") and fixed.count("\n") == code.rstrip().count("\n")


def test_valid_code_is_untouched() -> None:
    code = "def apply(df, ctx):\n    return df\n"
    assert strip_trailing_closer(code) == (code, False)


def test_other_syntax_errors_are_untouched() -> None:
    code = "def apply(df, ctx):\n    return (df\n"
    assert strip_trailing_closer(code) == (code, False)


async def test_a_repair_with_a_stray_brace_is_normalised_before_the_guard() -> None:
    good = "def apply(df, ctx):\n    return df.copy()"
    broken = good + "\n}"
    plan = make_plan()
    responses = {
        "coder:d1.keep": CoderOutput(code="import os\ndef apply(df, ctx):\n    return df"),
        "coder:d1.keep:repair": CoderOutput(code=broken),
        "coder:d1.trim": CoderOutput(code=good),
        "coder:m1.ols": CoderOutput(code=good.replace("apply", "estimate")),
        "coder:m1.welch": CoderOutput(code=good.replace("apply", "estimate")),
    }
    notes: list[tuple] = []

    async def on_coded(*args) -> None:
        notes.append(args)

    seen: list[str] = []
    real = coder.check_code

    def spy(code, kind):
        seen.append(code)
        return real(code, kind)

    coder.check_code = spy
    try:
        await code_plan(FakeLLM(responses), plan, on_coded)
    finally:
        coder.check_code = real
    assert all("\n}" not in code for code in seen)
    keep = next(n for n in notes if n[1] == "keep")
    assert keep[2] is True and "stray closing-bracket" in (keep[4] or "")
