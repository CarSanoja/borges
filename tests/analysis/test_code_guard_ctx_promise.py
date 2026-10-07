from __future__ import annotations

from borges.analysis.code_guard_ctx_promise import read_promise_violations
from tests.analysis.test_code_guard_ctx import plan, step

REL = step(
    "s5",
    "Relationship",
    "transform",
    "Create is_committed. Write to ctx['relationship_group_col'] = 'is_committed'.",
)
MODEL = step("m1", "Model", "model", "Fit Vote on df[ctx['relationship_group_col']].")
SILENT = (
    "def apply(df, ctx):\n    df['is_committed'] = df['Relationship'].isin([3, 4])\n    return df\n"
)
KEPT = SILENT.replace(
    "    return df", "    ctx['relationship_group_col'] = 'is_committed'\n    return df"
)


def test_a_promised_key_a_later_step_reads_must_be_written() -> None:
    """fertility_vote on 7 October, run 23: the key was promised, never written, and every model
    option failed with a KeyError."""
    found = read_promise_violations(SILENT, plan(REL, MODEL), REL, REL.options[0])
    assert found and "ctx['relationship_group_col']" in found[0] and "later step reads" in found[0]


def test_code_that_keeps_the_promise_passes() -> None:
    assert read_promise_violations(KEPT, plan(REL, MODEL), REL, REL.options[0]) == []


def test_a_promised_key_nobody_reads_is_not_held_to_the_spec() -> None:
    plain = step("m1", "Model", "model", "Fit Vote on is_committed.")
    assert read_promise_violations(SILENT, plan(REL, plain), REL, REL.options[0]) == []


def test_a_dynamic_write_is_trusted() -> None:
    dynamic = SILENT.replace(
        "    return df", "    ctx.update({'relationship_group_col': 'x'})\n    return df"
    )
    assert read_promise_violations(dynamic, plan(REL, MODEL), REL, REL.options[0]) == []
