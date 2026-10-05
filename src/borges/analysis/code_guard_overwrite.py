"""Model code that writes a column an earlier step produces.

An adversary quantile regression for marp_religiosity at 795bfb5 began with
df['religiosity'] = df[rel_cols].mean(axis=1): under the principal-component option it replaced
the component with the mean, so its "PCA" universes repeated the mean's estimate exactly. Reading
the product's name is not enough; assigning to it rebuilds it, unless the assigned value reads it
too, as df['cnorms'] = df['cnorms'].astype(float) does.
"""

from __future__ import annotations

import ast


def _target_names(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Subscript):
        key = target.slice
        if isinstance(key, ast.Tuple) and key.elts:
            key = key.elts[-1]
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            return {key.value}
    if isinstance(target, ast.Tuple | ast.List):
        return set().union(*(_target_names(t) for t in target.elts))
    return set()


def _reads(value: ast.AST) -> set[str]:
    return {
        n.value for n in ast.walk(value) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }


def overwritten(code: str, names: list[str]) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    written: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                written |= _target_names(target) - _reads(node.value)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            written |= _target_names(node.target) - _reads(node.value)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "assign"
        ):
            written |= {k.arg for k in node.keywords if k.arg and k.arg not in _reads(k.value)}
    return [name for name in names if name in written]
