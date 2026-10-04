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
