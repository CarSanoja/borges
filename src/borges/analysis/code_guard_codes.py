from __future__ import annotations

import ast
import re

ARITHMETIC = (ast.Mult, ast.Add, ast.Sub, ast.Div)
PROBLEM = (
    "line {line}: category codes number the levels in an arbitrary order (alphabetical or first "
    "seen), so a predictor built from them can reverse the sign of the estimate; build a 0/1 "
    "indicator for the level the estimand puts first, as (data[col] == 'committed').astype(float)"
)


def _coded(node: ast.AST) -> bool:
    for inner in ast.walk(node):
        if isinstance(inner, ast.Attribute) and inner.attr == "codes":
            return True
        if isinstance(inner, ast.Call):
            func = inner.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name == "factorize":
                return True
    return False


def _key(node: ast.AST) -> str | None:
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        value = node.slice.value
        return value if isinstance(value, str) else None
    return None


def _coded_names(tree: ast.AST) -> tuple[set[str], set[str]]:
    names: set[str] = set()
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _coded(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
                elif (key := _key(target)) is not None:
                    keys.add(key)
    return names, keys


def _refers(node: ast.AST, names: set[str], keys: set[str]) -> bool:
    if _coded(node):
        return True
    if isinstance(node, ast.Name):
        return node.id in names
    return _key(node) in keys


def _arithmetic(node: ast.AST, names: set[str], keys: set[str]) -> bool:
    if not (isinstance(node, ast.BinOp) and isinstance(node.op, ARITHMETIC)):
        return False
    return _refers(node.left, names, keys) or _refers(node.right, names, keys)


def _formula(node: ast.AST, keys: set[str]) -> bool:
    if not (isinstance(node, ast.Constant) and isinstance(node.value, str) and "~" in node.value):
        return False
    return any(re.search(rf"\b{re.escape(k)}\b", node.value) for k in keys)


def category_code_violations(tree: ast.AST) -> list[str]:
    """fertility_religiosity, 6 October 2026: a runtime repair of the OLS template coded the
    moderator rel_status as pd.Categorical(...).codes, which put 'committed' at 0 and 'single'
    at 1, so the reported interaction was single minus committed: the estimand with its sign
    reversed. Codes passed as cluster groups are left alone: there the order does not matter."""
    names, keys = _coded_names(tree)
    lines: set[int] = set()
    for node in ast.walk(tree):
        if _arithmetic(node, names, keys) or _formula(node, keys):
            lines.add(node.lineno)
    return [PROBLEM.format(line=line) for line in sorted(lines)]
