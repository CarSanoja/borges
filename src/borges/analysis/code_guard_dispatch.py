"""Methods named by a string that pandas then calls.

df.agg("to_csv", path), df.groupby(g).agg({"y": "to_pickle"}) and df.pipe("to_csv") reach a
method through getattr inside pandas, so the attribute check never sees the name. A string
handed to one of these dispatchers is held to the same rules as an attribute.
"""

from __future__ import annotations

import ast

from borges.analysis.code_guard_rules import (
    ALLOWED_TO_ATTRIBUTES,
    FORBIDDEN_ATTRIBUTES,
    FORBIDDEN_MODULES,
    IO_PREFIXES,
)

DISPATCHERS = frozenset({"agg", "aggregate", "apply", "applymap", "map", "transform", "pipe"})


def _forbidden(name: str) -> bool:
    if name.startswith("__") or name in FORBIDDEN_ATTRIBUTES or name in FORBIDDEN_MODULES:
        return True
    return name.startswith(IO_PREFIXES) and name not in ALLOWED_TO_ATTRIBUTES


def dispatch_violations(node: ast.Call) -> list[str]:
    if not isinstance(node.func, ast.Attribute) or node.func.attr not in DISPATCHERS:
        return []
    values = [*node.args, *(k.value for k in node.keywords)]
    names = {
        n.value
        for value in values
        for n in ast.walk(value)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and _forbidden(n.value)
    }
    return [
        f"line {node.lineno}: '{name}' passed to .{node.func.attr}() names a method pandas "
        "would call, and that method is not allowed; pass only statistics such as 'mean' by name"
        for name in sorted(names)
    ]
