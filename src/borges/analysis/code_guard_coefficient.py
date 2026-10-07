"""The estimate picked from a fitted model by position instead of by name.

A live fertility_religiosity run on 7 Oct 2026 repaired a model step into
`params.iloc[-1] if len(num_cov) > 0 else params["interaction"]`: with the covariates of the
default path the last coefficient was Sure2, so the run reported the Sure2 slope (0.169,
p .116) as the fertility x relationship interaction (0.362, p .745), and its minimal flip was
Sure2 turning significant. The position of a term depends on the covariates of each universe.
"""

from __future__ import annotations

import ast

VECTORS = {"params", "pvalues", "bse", "tvalues"}
INTERVALS = {"conf_int"}
MESSAGE = (
    "line {line}: the estimate is read from the fitted model by position ({text}), and the "
    "position of a term changes with the covariates of each universe; fit on a DataFrame with "
    "named columns and read params, pvalues and conf_int by the term's name"
)


def _kind(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Attribute) and node.attr in VECTORS:
        return "vector"
    if isinstance(node, ast.Attribute) and node.attr == "values":
        return "vector" if _kind(node.value, aliases) else None
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in INTERVALS
    ):
        return "interval"
    if isinstance(node, ast.Name):
        return aliases.get(node.id)
    return None


def _aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            kind = _kind(node.value, aliases)
            for target in node.targets:
                if kind and isinstance(target, ast.Name):
                    aliases[target.id] = kind
    return aliases


def _is_int(node: ast.AST) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        node = node.operand
    return isinstance(node, ast.Constant) and type(node.value) is int


def _row_index(node: ast.AST) -> ast.AST:
    return node.elts[0] if isinstance(node, ast.Tuple) and node.elts else node


def _positional(node: ast.Subscript, aliases: dict[str, str]) -> bool:
    value = node.value
    if isinstance(value, ast.Attribute) and value.attr == "iloc":
        row = _row_index(node.slice)
        return _kind(value.value, aliases) is not None and not isinstance(row, ast.Slice)
    if isinstance(value, ast.Attribute) and value.attr == "values":
        return _kind(value.value, aliases) is not None and _is_int(_row_index(node.slice))
    return _kind(value, aliases) == "vector" and _is_int(_row_index(node.slice))


def positional_estimate_violations(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    aliases = _aliases(tree)
    return [
        MESSAGE.format(line=node.lineno, text=ast.unparse(node))
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript) and _positional(node, aliases)
    ]
