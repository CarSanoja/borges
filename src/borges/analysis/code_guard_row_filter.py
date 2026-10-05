"""Rows removed by code whose spec removes none.

A bank_marketing_calls option at 027d581 had the spec "for each column in ['balance', 'duration',
'campaign', 'pdays', 'previous'], compute 1st and 99th percentiles, clip values below/above" and
code that also kept only rows with a known contact type and pdays >= 0: it dropped the 37,000
customers never contacted before, 82% of the data, under the label of a winsorizing option. A
frame the option returns may lose rows only when the spec says so, in words or in code. Among
1679 recorded option codes the rule found four more: two other winsorizing options that dropped
rows, a red_cards one that capped in its spec and dropped in its code, and a checkout one whose
spec was "Return the full dataframe unchanged" and whose code excluded internal sessions. The
other hits were hand-built scripted fixtures, which are not checked.
"""

from __future__ import annotations

import ast
import re

REMOVAL_INTENT = re.compile(
    r"\b(?:drop|remov|exclud|discard|delet|filter|keep|kept|retain|restrict|subset|select|only|"
    r"limit|trim|omit|dedup|duplicat|listwise|complete[- ]case|where|non-?missing|valid)\w*"
    r"|\bdf\s*\[\s*[~(]|\bdf\s*\[\s*df\b|\.(?:dropna|query|notna|notnull|isin|between)\b",
    re.IGNORECASE,
)
MASKS = (ast.Compare, ast.BoolOp, ast.UnaryOp)
ROW_CALLS = frozenset({"dropna", "query", "drop_duplicates"})


def _mask(node: ast.AST) -> bool:
    if isinstance(node, MASKS):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitAnd | ast.BitOr):
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and (node.func.attr in {"notna", "notnull", "isin", "between", "isna", "isnull"})
    )


def _removes_rows(value: ast.AST) -> bool:
    if isinstance(value, ast.Subscript):
        index = value.slice
        if isinstance(value.value, ast.Attribute) and value.value.attr == "loc":
            index = index.elts[0] if isinstance(index, ast.Tuple) else index
        return _mask(index)
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute):
        if value.func.attr in ROW_CALLS:
            return not any(k.arg == "axis" for k in value.keywords)
        return _removes_rows(value.func.value)
    return False


def _returned(tree: ast.AST) -> set[str]:
    return {
        node.value.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name)
    }


def row_filter_violations(code: str, spec: str) -> list[str]:
    if REMOVAL_INTENT.search(spec):
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    returned = _returned(tree) | {"df"}
    return [
        f"line {node.lineno}: the code removes rows ({ast.unparse(node.value)[:80]}) but the "
        "option's spec does not say to remove any; keep every row and do only what the spec says"
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id in returned for t in node.targets)
        and _removes_rows(node.value)
    ]
