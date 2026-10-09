"""The estimate picked from a fitted model by position instead of by name.

A live fertility_religiosity run on 7 Oct 2026 repaired a model step into
`params.iloc[-1] if len(num_cov) > 0 else params["interaction"]`: with the covariates of the
default path the last coefficient was Sure2, so the run reported the Sure2 slope (0.169,
p .116) as the fertility x relationship interaction (0.362, p .745), and its minimal flip was
Sure2 turning significant. The position of a term depends on the covariates of each universe.

A position found from the term's name, `fit.model.exog_names.index("new_protocol")` or
`params.index.get_loc(name)`, follows the term into every universe and is a read by name: a Cox
model's PHReg results are plain arrays, and a clinic run (r_20261009T092811_c73eca) lost every
option to this check for reading them that way.
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


LOOKUPS = {"index", "get_loc"}


def _lookup(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in LOOKUPS
        and len(node.args) == 1
    )


def _found_by_name(tree: ast.AST) -> set[str]:
    values: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values.setdefault(target.id, []).append(node.value)
    return {name for name, found in values.items() if all(_lookup(v) for v in found)}


def _is_int(node: ast.AST) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        node = node.operand
    return isinstance(node, ast.Constant) and type(node.value) is int


def _row_index(node: ast.AST) -> ast.AST:
    return node.elts[0] if isinstance(node, ast.Tuple) and node.elts else node


def _positional(node: ast.Subscript, aliases: dict[str, str], named: set[str]) -> bool:
    value = node.value
    if isinstance(value, ast.Attribute) and value.attr == "iloc":
        row = _row_index(node.slice)
        if _lookup(row) or (isinstance(row, ast.Name) and row.id in named):
            return False
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
    named = _found_by_name(tree)
    return [
        MESSAGE.format(line=node.lineno, text=ast.unparse(node))
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript) and _positional(node, aliases, named)
    ]
