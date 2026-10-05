"""Standardising each row across columns instead of each column across rows.

A marp_religiosity option at 027d581 promised to "standardise the nine rel_* items to z-scores"
and computed `(mat - mat.mean(axis=1)) / mat.std(axis=1)`: every respondent was z-scored across
their own nine items, which removes the respondent's overall religiosity, and the first principal
component of that matrix measured item profiles instead. Its standardised slope was half the item
mean's (0.045 against 0.093) and the run's minimal flip rested on it. Dividing by a standard
deviation taken across columns (axis=1) is flagged.
"""

from __future__ import annotations

import ast

SPREAD = frozenset({"std", "var", "nanstd", "nanvar"})


def _row_spread(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
    if name not in SPREAD:
        return False
    return any(
        k.arg == "axis" and isinstance(k.value, ast.Constant) and k.value.value in (1, "columns")
        for k in node.keywords
    )


def _mentions(node: ast.AST, names: set[str]) -> bool:
    return any(
        _row_spread(n) or (isinstance(n, ast.Name) and n.id in names) for n in ast.walk(node)
    )


def row_scale_violations(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    spreads: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _mentions(node.value, spreads):
            spreads.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return [
        f"line {node.lineno}: the code divides by a standard deviation taken across columns "
        "(axis=1), which z-scores each row across the items and removes each row's overall "
        "level; to standardise the items, scale each column across rows (axis=0)"
        for node in ast.walk(tree)
        if isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and _mentions(node.right, spreads)
    ]
