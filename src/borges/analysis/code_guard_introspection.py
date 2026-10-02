from __future__ import annotations

import ast

from borges.analysis.code_guard_rules import (
    INTROSPECTION_ATTRIBUTES,
    INTROSPECTION_NAMES,
    STRING_BUILDERS,
)


def attribute_violations(node: ast.Attribute) -> list[str]:
    attr = node.attr
    where = f"line {node.lineno}"
    if attr.startswith("_"):
        return [f"{where}: attribute '{attr}' starting with an underscore is not allowed"]
    if attr in INTROSPECTION_ATTRIBUTES:
        return [f"{where}: introspection attribute '{attr}' is not allowed"]
    return []


def name_violations(node: ast.Name) -> list[str]:
    if node.id in INTROSPECTION_NAMES:
        return [f"line {node.lineno}: use of '{node.id}' is not allowed"]
    return []


def _is_text(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _builds_string(key: ast.AST) -> bool:
    if isinstance(key, ast.JoinedStr):
        return True
    if isinstance(key, ast.BinOp):
        return _is_text(key.left) or _is_text(key.right) or _builds_string(key.left)
    if isinstance(key, ast.Call) and isinstance(key.func, ast.Attribute):
        return key.func.attr in STRING_BUILDERS and (
            _is_text(key.func.value) or isinstance(key.func.value, ast.BinOp)
        )
    return False


def subscript_violations(node: ast.Subscript) -> list[str]:
    if _builds_string(node.slice):
        return [f"line {node.lineno}: subscript with a computed string key is not allowed"]
    return []
