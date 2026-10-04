"""An unguarded first mode of a column.

Series.mode() is empty when the column has no non-missing values, which happens when an earlier
filter keeps only rows where it is missing (bank: pdays == -1 leaves poutcome all null), so
`.mode().iloc[0]` raises IndexError in that universe and the universe is lost.
"""

from __future__ import annotations

import ast


def _is_mode_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "mode"
    )


def _indexes_mode(node: ast.Subscript) -> bool:
    value = node.value
    if isinstance(value, ast.Attribute) and value.attr in ("iloc", "values", "loc"):
        value = value.value
    return _is_mode_call(value)


def empty_mode_violations(tree: ast.AST) -> list[str]:
    if any(isinstance(n, ast.Attribute) and n.attr == "empty" for n in ast.walk(tree)):
        return []
    return [
        f"line {node.lineno}: Series.mode() is empty when the column has no non-missing values "
        "(for example after an earlier filter), so taking its first element raises IndexError; "
        "check `if not mode.empty` first and leave the column unchanged otherwise"
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript) and _indexes_mode(node)
    ]
