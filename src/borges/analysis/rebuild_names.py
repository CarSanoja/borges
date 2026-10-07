"""Columns an option's code builds from scratch before it ever reads them.

fertility_vote on 7 October: the first step computed the cycle day and set it by hand for the two
participants whose dates are missing; the second step computed the cycle day again from the
dates, so those two rows became missing and were dropped, and the run reported a 301-row result
as the published analysis. Read on its own, the second step's code looked right. The harness
knows which columns arrive from earlier steps, so it refuses a step that rebuilds one of them
(`harness_rebuild.py`); this module finds the candidates in the code.

A name is rebuilt when its first mention in source order is a whole-column assignment
(df["x"] = ..., or .assign(x=...)) whose value does not read it. A partial update such as
df.loc[mask, "x"] = 0 keeps the other rows, so it counts as a read.
"""

from __future__ import annotations

import ast

Event = tuple[int, int, str, bool]


def _whole_column(target: ast.expr) -> ast.Constant | None:
    if not isinstance(target, ast.Subscript):
        return None
    key = target.slice
    if isinstance(key, ast.Constant) and isinstance(key.value, str):
        return key
    return None


def _strings(node: ast.AST) -> set[str]:
    return {
        n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }


def _writes(tree: ast.AST) -> tuple[list[Event], set[int]]:
    events: list[Event] = []
    keys: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign | ast.AnnAssign) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            read = _strings(node.value)
            for target in targets:
                key = _whole_column(target)
                if key is not None:
                    keys.add(id(key))
                    events.append((node.lineno, node.col_offset, key.value, key.value not in read))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "assign":
                for keyword in node.keywords:
                    if keyword.arg:
                        fresh = keyword.arg not in _strings(keyword.value)
                        events.append((node.lineno, node.col_offset, keyword.arg, fresh))
    return events, keys


def rebuilt_names(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    events, keys = _writes(tree)
    events += [
        (n.lineno, n.col_offset, n.value, False)
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in keys
    ]
    first: dict[str, bool] = {}
    for _, _, name, fresh in sorted(events, key=lambda e: (e[0], e[1], not e[3])):
        first.setdefault(name, fresh)
    return sorted(name for name, fresh in first.items() if fresh and name.isidentifier())
