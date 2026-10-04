from __future__ import annotations

import ast
import re

from borges.analysis.models import DatasetProfile

WIDE_LEVELS = 50


def wide_columns(profile: DatasetProfile | None) -> dict[str, int]:
    if profile is None:
        return {}
    return {c.name: c.n_unique for c in profile.columns if c.n_unique > WIDE_LEVELS}


def _names_in(node: ast.AST) -> set[str]:
    return {
        n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }


def _dummy_coded(tree: ast.AST, name: str) -> bool:
    pattern = re.compile(rf"\bC\(\s*{re.escape(name)}\b")
    for node in ast.walk(tree):
        text = isinstance(node, ast.Constant) and isinstance(node.value, str)
        if text and pattern.search(node.value):
            return True
        if isinstance(node, ast.Call):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if called == "get_dummies" and name in _names_in(node):
                return True
    return False


def wide_dummy_violations(code: str, wide: dict[str, int]) -> list[str]:
    if not wide:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    return [
        f"'{name}' has {levels} distinct values: dummy-coding it (C({name}) or get_dummies) "
        f"builds {levels} columns, which does not fit in the sandbox and adds {levels} nuisance "
        f"parameters; cluster the standard errors on it (cov_type='cluster', groups from "
        f"'{name}') or leave it out"
        for name, levels in sorted(wide.items())
        if _dummy_coded(tree, name)
    ]
