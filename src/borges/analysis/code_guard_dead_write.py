"""Rows set by hand that a later whole-column assignment wipes out.

fertility_vote on 7 October, run 28: the cycle-day step set WorkerID 15 and 16 to days 11 and 18
with df.loc[df['WorkerID'] == 15, 'cycle_day'] = 11, then assigned df['cycle_day'] = cycle_day
for every row, so the two women got the computed day (missing, as their period dates are) and the
window filter dropped them. The spec was right; the starting point fitted 301 women, not 303. A
write to some rows of a column, followed in the same block by an assignment of the whole column
that does not read it, with nothing reading the column in between, is reported.
"""

from __future__ import annotations

import ast
import re

from borges.analysis.models import AnalysisPlan, Step

ROW_INDEXERS = ("loc", "at", "iloc", "iat")
FILLS = ("fillna", "combine_first", "where", "mask", "insert", "interpolate", "ffill", "bfill")
WORD = re.compile(r"[A-Za-z_]\w*")
ONLY_NAMED = (
    "column '{column}' is created only by setting rows named one by one (line {line}), so every "
    "other row has no value; assign the whole column from its computation first and set those "
    "rows after it"
)
MESSAGE = (
    "line {first} sets column '{column}' for some rows, and line {second} assigns the whole column "
    "without reading it, so the rows set on line {first} lose their value; build the whole column "
    "first and set those rows after it"
)


def _frame_and_column(target: ast.expr) -> tuple[str, str, bool] | None:
    """(frame name, column, whole column) for df['c'], df.loc[:, 'c'] or df.loc[rows, 'c']."""
    if not isinstance(target, ast.Subscript):
        return None
    holder, key = target.value, target.slice
    if isinstance(holder, ast.Name) and isinstance(key, ast.Constant):
        return (holder.id, key.value, True) if isinstance(key.value, str) else None
    if not (
        isinstance(holder, ast.Attribute)
        and holder.attr in ROW_INDEXERS
        and isinstance(holder.value, ast.Name)
        and isinstance(key, ast.Tuple)
        and len(key.elts) == 2
    ):
        return None
    rows, column = key.elts
    if not (isinstance(column, ast.Constant) and isinstance(column.value, str)):
        return None
    whole = isinstance(rows, ast.Slice) and rows.lower is None and rows.upper is None
    return holder.value.id, column.value, whole


def _mentions(node: ast.AST, column: str, frame: str) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and n.value == column:
            return True
        if isinstance(n, ast.Attribute) and n.attr == column:
            return True
        if isinstance(n, ast.Name) and n.id == frame and isinstance(n.ctx, ast.Store):
            return True
    return False


def _block(body: list[ast.stmt]) -> list[str]:
    found: list[str] = []
    for i, stmt in enumerate(body):
        if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1):
            continue
        first = _frame_and_column(stmt.targets[0])
        if first is None or first[2]:
            continue
        frame, column, _ = first
        for later in body[i + 1 :]:
            if isinstance(later, ast.Assign) and len(later.targets) == 1:
                second = _frame_and_column(later.targets[0])
                if second == (frame, column, True) and not _mentions(later.value, column, frame):
                    found.append(
                        MESSAGE.format(first=stmt.lineno, second=later.lineno, column=column)
                    )
                    break
            if _mentions(later, column, frame):
                break
    return found


def dead_write_violations(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    found: list[str] = []
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if isinstance(block, list) and block and isinstance(block[0], ast.stmt):
                found.extend(_block(block))
    return found


def _literal_rows(rows: ast.expr) -> bool:
    """A selector like df['id'] == 15 or df['id'].isin([15, 16])."""
    if isinstance(rows, ast.Compare) and len(rows.ops) == 1 and isinstance(rows.ops[0], ast.Eq):
        return isinstance(rows.comparators[0], ast.Constant)
    if isinstance(rows, ast.Call) and isinstance(rows.func, ast.Attribute):
        values = rows.args[0] if rows.func.attr == "isin" and rows.args else None
        return isinstance(values, ast.List | ast.Tuple | ast.Set) and all(
            isinstance(v, ast.Constant) for v in values.elts
        )
    return False


def _named_row_writes(tree: ast.AST) -> dict[str, list[tuple[int, bool]]]:
    found: dict[str, list[tuple[int, bool]]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            hit = _frame_and_column(target)
            if hit is None or hit[2]:
                continue
            assert isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Tuple)
            named = _literal_rows(target.slice.elts[0])
            found.setdefault(hit[1], []).append((node.lineno, named))
    return found


def _filled(tree: ast.AST, column: str) -> bool:
    """A whole-column write, an .assign or .insert of it, or a fill call that names it."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                hit = _frame_and_column(target)
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


def _known(plan: AnalysisPlan, step: Step) -> set[str]:
    known = {c.name for c in plan.dataset.columns}
    for earlier in plan.steps[: plan.steps.index(step)]:
        known |= set(earlier.produces)
        for option in earlier.options:
            known |= set(WORD.findall(f"{option.spec}\n{option.code or ''}"))
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
