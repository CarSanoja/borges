"""A new column whose only values are the rows set by hand.

fertility_vote on 7 October, runs 30, 31, 34 and 38: the step kept the computed cycle days in a
local variable and created the column only by setting the two women's rows (by WorkerID, through
a selector variable, or by position), so every other row had no cycle day; one run kept only
those two rows, the others passed on an empty column and the model's fertility indicator was all
zeros. A column that is not in the data, not produced by an earlier step and not written by an
earlier step's code, whose only writes set rows named one by one with literal values, and that
nothing fills, is reported.
"""

from __future__ import annotations

import ast

from borges.analysis.code_guard_dead_write import frame_and_column
from borges.analysis.models import AnalysisPlan, Step

FILLS = ("fillna", "combine_first", "where", "mask", "insert", "interpolate", "ffill", "bfill")
ONLY_NAMED = (
    "column '{column}' is created only by setting rows named one by one (line {line}), so every "
    "other row has no value; assign the whole column from its computation first and set those "
    "rows after it"
)


def _literal_rows(rows: ast.expr) -> bool:
    """A selector like df['id'] == 15, df['id'].isin([15, 16]), or the labels [15, 16]."""
    if isinstance(rows, ast.Constant) and not isinstance(rows.value, str):
        return True
    if isinstance(rows, ast.List | ast.Tuple) and rows.elts:
        return all(isinstance(v, ast.Constant) for v in rows.elts)
    if isinstance(rows, ast.Compare) and len(rows.ops) == 1 and isinstance(rows.ops[0], ast.Eq):
        return isinstance(rows.comparators[0], ast.Constant)
    if isinstance(rows, ast.Call) and isinstance(rows.func, ast.Attribute):
        values = rows.args[0] if rows.func.attr == "isin" and rows.args else None
        return isinstance(values, ast.List | ast.Tuple | ast.Set) and all(
            isinstance(v, ast.Constant) for v in values.elts
        )
    return False


def _literal_names(tree: ast.AST) -> set[str]:
    return {
        t.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and _literal_rows(node.value)
        for t in node.targets
        if isinstance(t, ast.Name)
    }


def _named_row_writes(tree: ast.AST) -> dict[str, list[tuple[int, bool]]]:
    found: dict[str, list[tuple[int, bool]]] = {}
    literal = _literal_names(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            hit = frame_and_column(target)
            if hit is None or hit[2]:
                continue
            assert isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Tuple)
            rows = target.slice.elts[0]
            named = _literal_rows(rows) or (isinstance(rows, ast.Name) and rows.id in literal)
            found.setdefault(hit[1], []).append((node.lineno, named))
    return found


def _filled(tree: ast.AST, column: str) -> bool:
    """A whole-column write, an .assign or .insert of it, or a fill call that names it."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                hit = frame_and_column(target)
                if hit is not None and hit[1] == column and hit[2]:
                    return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "assign" and any(k.arg == column for k in node.keywords):
                return True
            if node.func.attr in FILLS and any(
                isinstance(n, ast.Constant) and n.value == column for n in ast.walk(node)
            ):
                return True
    return False


def _written(code: str | None) -> set[str]:
    try:
        tree = ast.parse(code or "")
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names |= {hit[1] for t in node.targets if (hit := frame_and_column(t)) is not None}
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "assign"
        ):
            names |= {k.arg for k in node.keywords if k.arg}
    return names


def _known(plan: AnalysisPlan, step: Step) -> set[str]:
    """The data's columns, what earlier steps produce, and what their code writes."""
    known = {c.name for c in plan.dataset.columns}
    for earlier in plan.steps[: plan.steps.index(step)]:
        known |= set(earlier.produces)
        for option in earlier.options:
            known |= _written(option.code)
    return known


def named_rows_only_violations(code: str, plan: AnalysisPlan, step: Step) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    known = _known(plan, step) if step in plan.steps else set()
    found = []
    for column, writes in _named_row_writes(tree).items():
        if column in known or not all(named for _, named in writes):
            continue
        if _filled(tree, column):
            continue
        found.append(ONLY_NAMED.format(column=column, line=min(line for line, _ in writes)))
    return found
