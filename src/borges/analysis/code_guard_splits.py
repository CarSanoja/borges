from __future__ import annotations

import ast

SPLIT_OPS = (ast.Eq, ast.NotEq)


def _column_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        return node.slice.value if isinstance(node.slice.value, str) else None
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.attr
    return None


def split_key(selector: ast.expr) -> tuple[str, str] | None:
    if not isinstance(selector, ast.Compare) or len(selector.ops) != 1:
        return None
    if not isinstance(selector.ops[0], SPLIT_OPS):
        return None
    column = _column_name(selector.left)
    right = selector.comparators[0]
    if column is None or not isinstance(right, ast.Constant):
        return None
    return column, repr(right.value)


def _unwrap_copy(node: ast.expr) -> ast.expr:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "copy"
        and not node.args
    ):
        return node.func.value
    return node


def _selection(value: ast.expr) -> tuple[ast.Subscript, ast.expr] | None:
    node = _unwrap_copy(value)
    if not isinstance(node, ast.Subscript):
        return None
    selector = node.slice
    if isinstance(selector, ast.Tuple) and selector.elts:
        selector = selector.elts[0]
    return node, selector


def group_split_nodes(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[int]:
    own = {a.arg for a in func.args.args}
    found: dict[str, list[tuple[str, int]]] = {}
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id in own:
            continue
        picked = _selection(node.value)
        key = split_key(picked[1]) if picked else None
        if picked and key:
            found.setdefault(key[0], []).append((key[1], id(picked[0])))
    exempt: set[int] = set()
    for entries in found.values():
        if len({value for value, _ in entries}) >= 2:
            exempt.update(node_id for _, node_id in entries)
    return exempt


def column_names(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if (
                isinstance(target, ast.Name)
                and isinstance(node.value, ast.Subscript)
                and _column_name(node.value) is not None
            ):
                names.add(target.id)
    return names


def is_column_base(node: ast.expr, names: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in names
    return isinstance(node, ast.Subscript) and _column_name(node) is not None


def _method(node: ast.Call) -> str | None:
    return node.func.attr if isinstance(node.func, ast.Attribute) else None


def is_group_filter(node: ast.Call) -> bool:
    if _method(node) != "filter" or not isinstance(node.func, ast.Attribute):
        return False
    inner = node.func.value
    return isinstance(inner, ast.Call) and _method(inner) == "groupby"
