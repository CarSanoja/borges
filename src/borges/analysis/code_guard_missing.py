from __future__ import annotations

import ast
import re

MISSING = r"(?:missing|NA|NaN|null|incomplete)"
DROP_INTENT = re.compile(
    rf"\b(?:drop|remove|exclude|discard|delete)\w*\b[^.;]{{0,80}}\b{MISSING}\b"
    r"|\bcomplete[- ]case\b|\blistwise\b",
    re.IGNORECASE,
)
FILL_INTENT = re.compile(
    rf"\bimput\w*|\bfill\w*\b|\b{MISSING}[- ](?:value )?(?:indicator|flag|category)"
    rf"|\b(?:indicator|flag)s? (?:for|of) {MISSING}|\breplace\w*\b[^.;]{{0,40}}\b{MISSING}\b",
    re.IGNORECASE,
)
DROPS = frozenset({"dropna", "notna", "notnull", "isna", "isnull", "query"})
FILLS = frozenset({"fillna", "SimpleImputer", "IterativeImputer", "KNNImputer", "interpolate"})


def _called(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            names.add(func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", ""))
    return names


def _filters(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load):
            inner = {
                n.func.attr
                for n in ast.walk(node.slice)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            }
            if inner & DROPS:
                return True
    return False


def missing_violations(code: str, intent: str) -> list[str]:
    drops, fills = bool(DROP_INTENT.search(intent)), bool(FILL_INTENT.search(intent))
    if drops == fills:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    called = _called(tree)
    removes = "dropna" in called or _filters(tree)
    imputes = bool(called & FILLS)
    if drops and imputes and not removes:
        return [
            "the option drops rows with missing values, but this code fills them instead and "
            "removes no row; drop those rows (for example df.dropna(subset=[...])) as the "
            "option says"
        ]
    if fills and removes and not imputes:
        return [
            "the option keeps rows with missing values and fills or flags them, but this code "
            "removes rows instead; fill or flag the missing values as the option says"
        ]
    return []
