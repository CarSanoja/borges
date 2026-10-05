"""Rows removed by code whose spec removes none.

A bank_marketing_calls option at 027d581 had the spec "for each column in ['balance', 'duration',
'campaign', 'pdays', 'previous'], compute 1st and 99th percentiles, clip values below/above" and
code that also kept only rows with a known contact type and pdays >= 0: it dropped the 37,000
customers never contacted before, 82% of the data, under the label of a winsorizing option. A
frame the option returns may lose rows only when the spec says so, in words or in code. Among
1679 recorded option codes the rule found four more: two other winsorizing options that dropped
rows, a red_cards one that capped in its spec and dropped in its code, and a checkout one whose
spec was "Return the full dataframe unchanged" and whose code excluded internal sessions.
Dropping the rows that miss a value the code itself transforms into a new column is the complete
case of that transform and is allowed: the scripted marp scaling options drop rows missing wb, rel
or norm before z-scoring them, and the model would drop those rows anyway.
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


def _strings(node: ast.AST, names: dict[str, ast.AST]) -> set[str]:
    if isinstance(node, ast.Name) and node.id in names:
        node = names[node.id]
    return {
        n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }


def _writes_column(node: ast.AST) -> bool:
    return isinstance(node, ast.Assign) and any(isinstance(t, ast.Subscript) for t in node.targets)


def _transformed(tree: ast.AST) -> set[str]:
    read: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and any(_writes_column(n) for n in ast.walk(node)):
            read |= _strings(node.iter, {})
        if _writes_column(node):
            read |= {
                n.slice.value
                for n in ast.walk(node.value)
                if isinstance(n, ast.Subscript)
                and isinstance(n.slice, ast.Constant)
                and isinstance(n.slice.value, str)
            }
    return read


def _complete_case(value: ast.AST, tree: ast.AST) -> bool:
    if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)):
        return False
    if value.func.attr != "dropna":
        return False
    subset = next((k.value for k in value.keywords if k.arg == "subset"), None)
    if subset is None:
        return False
    names = {
        t.id: node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for t in node.targets
        if isinstance(t, ast.Name)
    }
    columns = _strings(subset, names)
    return bool(columns) and columns <= _transformed(tree)


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
        and not _complete_case(node.value, tree)
    ]
