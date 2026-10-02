from __future__ import annotations

import ast

MISSING_CALLS = frozenset({"isna", "notna", "isnull", "notnull"})
VALUE_CALLS = frozenset(
    {
        "isin",
        "between",
        "contains",
        "startswith",
        "endswith",
        "eq",
        "ne",
        "lt",
        "le",
        "gt",
        "ge",
        "duplicated",
    }
)
RESULT_ATTRIBUTES = frozenset(
    {"params", "pvalues", "bse", "tvalues", "resid", "fittedvalues", "conf_int", "summary"}
)
FIT_CALLS = frozenset({"fit", "fit_regularized", "get_robustcov_results"})
MESSAGE = (
    "a model step may only drop incomplete rows; this filters rows by value, which is a "
    "decision that belongs to a filter step: remove it"
)
Kind = str | None


def _merge(kinds: list[Kind]) -> Kind:
    if "value" in kinds:
        return "value"
    if "missing" in kinds:
        return "missing"
    return None


def _call_attr(node: ast.Call) -> str | None:
    return node.func.attr if isinstance(node.func, ast.Attribute) else None


def mask_kind(node: ast.expr, names: dict[str, str]) -> Kind:
    if isinstance(node, ast.Compare):
        return "value"
    if isinstance(node, ast.BoolOp):
        return _merge([mask_kind(v, names) for v in node.values])
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not | ast.Invert):
        return mask_kind(node.operand, names)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitAnd | ast.BitOr | ast.BitXor):
        return _merge([mask_kind(node.left, names), mask_kind(node.right, names)])
    if isinstance(node, ast.Name):
        return names.get(node.id)
    if isinstance(node, ast.Call):
        attr = _call_attr(node)
        if attr in MISSING_CALLS:
            return "missing"
        if attr in VALUE_CALLS:
            return "value"
        if attr in {"all", "any"} and isinstance(node.func, ast.Attribute):
            return mask_kind(node.func.value, names)
    return None


def _collect_names(func: ast.AST) -> tuple[dict[str, str], set[str]]:
    masks: dict[str, str] = {}
    results: set[str] = set()
    for _ in range(2):
        for node in ast.walk(func):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            kind = mask_kind(node.value, masks)
            if kind is not None:
                masks[target.id] = kind
            if _is_fit_chain(node.value):
                results.add(target.id)
    return masks, results


def _is_fit_chain(node: ast.expr) -> bool:
    return isinstance(node, ast.Call) and _call_attr(node) in FIT_CALLS


def _result_like(node: ast.expr, results: set[str]) -> bool:
    current: ast.expr = node
    while True:
        if isinstance(current, ast.Attribute):
            if current.attr in RESULT_ATTRIBUTES:
                return True
            current = current.value
        elif isinstance(current, ast.Subscript | ast.Call):
            current = current.value if isinstance(current, ast.Subscript) else current.func
        elif isinstance(current, ast.Name):
            return current.id in results
        else:
            return False


def _row_selector(node: ast.Subscript) -> ast.expr:
    selector = node.slice
    if isinstance(selector, ast.Tuple) and selector.elts:
        return selector.elts[0]
    return selector


def _is_indexer(node: ast.Subscript) -> bool:
    return isinstance(node.value, ast.Attribute) and node.value.attr in {"loc", "iloc"}


def _extracts_column(node: ast.Subscript, parent: ast.AST | None) -> bool:
    if _is_indexer(node):
        selector = node.slice
        return (
            isinstance(selector, ast.Tuple)
            and len(selector.elts) == 2
            and isinstance(selector.elts[1], ast.Constant)
            and isinstance(selector.elts[1].value, str)
        )
    return (
        isinstance(parent, ast.Subscript)
        and parent.value is node
        and isinstance(parent.slice, ast.Constant)
        and isinstance(parent.slice.value, str)
    )


def _subscript_error(
    node: ast.Subscript, parent: ast.AST | None, masks: dict[str, str], results: set[str]
) -> str | None:
    if not isinstance(node.ctx, ast.Load):
        return None
    base = (
        node.value.value
        if _is_indexer(node) and isinstance(node.value, ast.Attribute)
        else node.value
    )
    if _result_like(base, results):
        return None
    if mask_kind(_row_selector(node), masks) != "value":
        return None
    if _extracts_column(node, parent):
        return None
    return f"line {node.lineno}: row filter `{ast.unparse(node)}`: {MESSAGE}"


def _query_error(node: ast.Call, results: set[str]) -> str | None:
    if _call_attr(node) != "query" or not isinstance(node.func, ast.Attribute):
        return None
    if _result_like(node.func.value, results):
        return None
    return f"line {node.lineno}: row filter `{ast.unparse(node)}`: {MESSAGE}"


def row_filter_violations(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    masks, results = _collect_names(func)
    violations: list[str] = []
    parents = {id(child): node for node in ast.walk(func) for child in ast.iter_child_nodes(node)}
    for node in ast.walk(func):
        found = None
        if isinstance(node, ast.Subscript):
            found = _subscript_error(node, parents.get(id(node)), masks, results)
        elif isinstance(node, ast.Call):
            found = _query_error(node, results)
        if found and found not in violations:
            violations.append(found)
    return violations
