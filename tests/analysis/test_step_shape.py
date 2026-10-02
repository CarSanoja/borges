from __future__ import annotations

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
