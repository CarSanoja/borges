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

ROW_INDEXERS = ("loc", "at", "iloc", "iat")
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
