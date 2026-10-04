from __future__ import annotations

import pytest

from borges.analysis.code_guard_ctx_names import ctx_name_violations
from borges.analysis.models import Option, Step

SPEC = (
    "Compute religiosity as the item mean; write to ctx['religiosity']; add column 'religiosity'."
)


def step() -> Step:
    option = Option(id="o", label="Mean", rationale="r", spec=SPEC, is_default=True)
    return Step(
        id="s",
        title="Religiosity",
        kind="transform",
        description="d",
        produces=["religiosity"],
        options=[option],
    )


def body(line: str) -> str:
    return (
        "def apply(df, ctx):\n"
        "    df = df.copy()\n"
        "    df['religiosity'] = df[['rel_1', 'rel_2']].mean(axis=1)\n"
        f"{line}"
        "    return df\n"
    )


def test_the_column_name_in_ctx_passes() -> None:
    s = step()
    assert (
        ctx_name_violations(body("    ctx['religiosity'] = 'religiosity'\n"), s, s.options[0]) == []
    )


@pytest.mark.parametrize(
    ("line", "held"),
    [
        ("    ctx['religiosity'] = 'mean'\n", "'mean'"),
        ("    ctx['religiosity'] = df['religiosity']\n", "df['religiosity']"),
        ("", "nothing"),
    ],
)
def test_anything_else_in_ctx_is_refused(line: str, held: str) -> None:
    s = step()
    found = ctx_name_violations(body(line), s, s.options[0])
    assert len(found) == 1 and f"puts {held} there" in found[0]
    assert "set ctx['religiosity'] = 'religiosity'" in found[0]


def test_a_spec_that_never_names_the_ctx_entry_is_not_checked() -> None:
    s = step()
    option = s.options[0].model_copy(update={"spec": "Add column 'religiosity' as the mean."})
    assert ctx_name_violations(body(""), s, option) == []
