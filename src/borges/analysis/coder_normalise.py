from __future__ import annotations

import ast

CLOSERS = frozenset("}])")


def _parses(code: str) -> bool:
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    return True


def strip_trailing_closer(code: str) -> tuple[str, bool]:
    if _parses(code):
        return code, False
    lines = code.rstrip().split("\n")
    last = lines[-1].strip()
    if not last or any(char not in CLOSERS for char in last):
        return code, False
    trimmed = "\n".join(lines[:-1]).rstrip() + "\n"
    if not _parses(trimmed):
        return code, False
    return trimmed, True


ALIASES = {
    "pd": "import pandas as pd",
    "np": "import numpy as np",
    "sm": "import statsmodels.api as sm",
    "smf": "import statsmodels.formula.api as smf",
    "stats": "from scipy import stats",
    "math": "import math",
}


def _bound_names(tree: ast.AST) -> set[str]:
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            bound.update((a.asname or a.name).split(".")[0] for a in node.names)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.FunctionDef | ast.ClassDef):
            bound.add(node.name)
    return bound


def add_missing_imports(code: str) -> tuple[str, bool]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code, False
    used = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    missing = sorted(used.intersection(ALIASES) - _bound_names(tree))
    if not missing:
        return code, False
    header = "\n".join(ALIASES[name] for name in missing)
    return header + "\n" + code, True
