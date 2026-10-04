from __future__ import annotations

import ast
import re

from borges.analysis.models import AnalysisPlan, Step

CTX_WRITE = re.compile(r"""ctx\s*\[\s*["'](\w+)["']\s*\]\s*(?:\+=|=(?!=)|\.extend\()\s*([^;\n]*)""")
UNADJUSTED = re.compile(
    r"\bunadjusted\b|\bno covariates\b|\bwithout (?:any )?covariates\b|\bcovariates? ignored\b",
    re.IGNORECASE,
)


def _read_pattern(key: str) -> re.Pattern[str]:
    return re.compile(rf"""ctx\s*(?:\[\s*|\.get\(\s*)["']{key}["'](?!\s*\]\s*(?:=(?!=)|\+=))""")


def _writes(text: str) -> dict[str, str]:
    return {key: " ".join(value.split()) for key, value in CTX_WRITE.findall(text)}


def _text(step: Step) -> list[str]:
    return [option.code or option.spec for option in step.options]


def varying_ctx_keys(plan: AnalysisPlan, step: Step) -> dict[str, str]:
    found: dict[str, str] = {}
    earlier = plan.steps[: next(i for i, s in enumerate(plan.steps) if s.id == step.id)]
    for index, writer in enumerate(earlier):
        writes = [_writes(text) for text in _text(writer)]
        for key in set().union(*writes):
            if len({w.get(key) for w in writes}) < 2:
                continue
            reader = _read_pattern(key)
            later = [t for s in earlier[index + 1 :] for t in _text(s)]
            if not any(reader.search(t) for t in later):
                found.setdefault(key, writer.title)
    return found


def _ctx_access(node: ast.AST) -> ast.expr | None:
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        return node.slice if node.value.id == "ctx" else None
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args:
        owner = node.func.value
        if node.func.attr == "get" and isinstance(owner, ast.Name) and owner.id == "ctx":
            return node.args[0]
    return None


def _read_keys(tree: ast.AST) -> set[str] | None:
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            continue
        key = _ctx_access(node)
        if key is None:
            continue
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            return None
        keys.add(key.value)
    return keys


def ctx_read_violations(code: str, keys: dict[str, str], intent: str) -> list[str]:
    if not keys:
        return []
    try:
        read = _read_keys(ast.parse(code))
    except SyntaxError:
        return []
    if read is None:
        return []
    skip = {"covariates"} if UNADJUSTED.search(intent) else set()
    return [
        f"the earlier step '{title}' sets ctx['{key}'] differently in each of its options, but "
        f"this code never reads it, so that choice would have no effect in this option; read "
        f"ctx.get('{key}') and use it as the option describes"
        for key, title in sorted(keys.items())
        if key not in read and key not in skip
    ]
