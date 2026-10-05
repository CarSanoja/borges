from __future__ import annotations

import ast

BROAD = frozenset({"Exception", "BaseException"})
FITS = frozenset({"fit", "fit_regularized"})


def _broad(handler: ast.ExceptHandler) -> bool:
    kind = handler.type
    if kind is None:
        return True
    names = kind.elts if isinstance(kind, ast.Tuple) else [kind]
    return any(isinstance(n, ast.Name) and n.id in BROAD for n in names)


def _fits(nodes: list[ast.stmt]) -> bool:
    for statement in nodes:
        for node in ast.walk(statement):
            call = isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            if call and node.func.attr in FITS:
                return True
    return False


def fallback_violations(tree: ast.AST) -> list[str]:
    return [
        f"line {handler.lineno}: an except clause that fits another model when the first one "
        "fails silently changes the analysis; let the error surface so the option fails visibly"
        for node in ast.walk(tree)
        if isinstance(node, ast.Try)
        for handler in node.handlers
        if _broad(handler) and _fits(handler.body)
    ]


CHECKS = frozenset({"isfinite", "isnan", "isinf"})
INVENTED = frozenset({"eye", "identity"})
P_NAMES = frozenset({"p_value", "p", "pval", "p_val", "pvalue"})


def _called(node: ast.AST, names: frozenset[str]) -> bool:
    for inner in ast.walk(node):
        if isinstance(inner, ast.Call):
            func = inner.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name in names:
                return True
    return False


def _fixed(value: ast.expr) -> bool:
    if isinstance(value, ast.UnaryOp):
        value = value.operand
    if isinstance(value, ast.Constant):
        return isinstance(value.value, int | float) and not isinstance(value.value, bool)
    return _called(value, INVENTED)


def _invented(body: list[ast.stmt]) -> list[ast.Assign]:
    if any(isinstance(node, ast.Raise) for s in body for node in ast.walk(s)):
        return []
    return [s for s in body if isinstance(s, ast.Assign) and _fixed(s.value)]


def substituted_value_violations(tree: ast.AST) -> list[str]:
    """A bank_marketing_calls 'Bayesian logistic regression' at 2415a4b, after a runtime repair,
    set the coefficient to 0 and its variance to 1 when the fit was not finite: that universe
    reported OR 1.05 [0.15, 7.8], a made-up null that became the run's direction flip."""
    branches = [
        node.body
        for node in ast.walk(tree)
        if isinstance(node, ast.If) and _called(node.test, CHECKS)
    ]
    branches += [
        h.body for node in ast.walk(tree) if isinstance(node, ast.Try) for h in node.handlers
    ]
    return [
        f"line {s.lineno}: when the fit fails or is not finite the code substitutes fixed values "
        f"({ast.unparse(s)}), which invents a result; raise a ValueError so the option fails"
        for body in branches
        for s in _invented(body)
    ]


def _share(value: ast.expr) -> bool:
    while isinstance(value, ast.Call) and getattr(value.func, "id", None) == "float" and value.args:
        value = value.args[0]
    if not isinstance(value, ast.Call):
        return False
    func = value.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    if name != "mean":
        return False
    inner = value.args[0] if value.args else getattr(func, "value", None)
    return isinstance(inner, ast.Compare)


def share_p_value_violations(tree: ast.AST) -> list[str]:
    """The same option returned the share of posterior draws above 1 as its p-value."""
    return [
        f"line {node.lineno}: {ast.unparse(node.targets[0])} is the share of draws on one side, "
        "not a two-sided p-value for the null of no effect; for draws use 2 * min(share, 1 - share)"
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in P_NAMES
        and _share(node.value)
    ]
