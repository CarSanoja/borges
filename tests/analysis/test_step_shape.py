from __future__ import annotations

import re

import pytest

from borges.analysis.harness import render_step
from borges.analysis.models import Option, Step
from borges.analysis.step_shape import is_rendered_step
from tests.gateway.rendered import rendered_step

BODY = "def estimate(df, ctx):\n    return {}"


def test_a_rendered_step_matches_its_body() -> None:
    assert is_rendered_step(rendered_step(BODY + "\n"), BODY)
    assert is_rendered_step(rendered_step(BODY, "/h", "/a.jsonl"), BODY)


def test_extra_code_around_the_rendered_step_is_rejected() -> None:
    text = rendered_step(BODY)
    assert not is_rendered_step(text + "\nimport os\n", BODY)
    assert not is_rendered_step("import os\n" + text, BODY)


def test_a_swapped_body_is_rejected() -> None:
    assert not is_rendered_step(rendered_step("def estimate(df, ctx):\n    return 1"), BODY)


def test_a_forged_prelude_is_rejected() -> None:
    text = rendered_step(BODY)
    _, rest = text.split("\n", 1)
    assert not is_rendered_step(
        "exec(compile('import os', '<borges-policy>', 'exec'), {})\n" + rest, BODY
    )


@pytest.mark.parametrize(
    "flags",
    [{}, {"standardised": True}, {"split_half": True}, {"design_check": False}],
)
def test_every_rendering_of_a_step_is_recognised(flags: dict[str, bool]) -> None:
    option = Option(id="o", label="l", rationale="r", spec="s", is_default=True, code=BODY)
    step = Step(id="model", title="t", kind="model", description="d", options=[option])
    text = render_step(step, option, **flags)
    assert re.search(r"__[A-Z][A-Z_]*__", text) is None
    assert is_rendered_step(text, BODY)
