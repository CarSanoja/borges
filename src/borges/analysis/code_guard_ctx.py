from __future__ import annotations

import ast
import re

from borges.analysis.models import AnalysisPlan, Step

CTX_WRITE = re.compile(r"""ctx\s*\[\s*["'](\w+)["']\s*\]\s*(?:\+=|=(?!=)|\.extend\()\s*([^;\n]*)""")
LITERAL = r"""(\[[^\]]*\]|["'][^"']+["'])"""
KEY = r"""ctx\s*\[\s*["'](\w+)["']\s*\]"""
PROSE_WRITE = re.compile(
    rf"\b(?:write|store|save|put|record)s?\s+{LITERAL}\s+(?:to|in|into|as|under)\s+{KEY}",
    re.IGNORECASE,
)
PROSE_SET = re.compile(rf"\bsets?\s+{KEY}\s+to\s+{LITERAL}", re.IGNORECASE)
UNADJUSTED = re.compile(
    r"\bunadjusted\b|\bno covariates\b|\bwithout (?:any )?covariates\b|\bcovariates? ignored\b",
    re.IGNORECASE,
)


def ctx_read_pattern(key: str) -> re.Pattern[str]:
    return re.compile(rf"""ctx\s*(?:\[\s*|\.get\(\s*)["']{key}["'](?!\s*\]\s*(?:=(?!=)|\+=))""")


COLUMN_KEYS = frozenset({"covariates", "outcome"})
CREATED = re.compile(r"""df\s*\[\s*["'](\w+)["']\s*\]\s*=(?!=)""")


def ctx_writes(text: str) -> dict[str, str]:
    """What a piece of code, or a spec in code or in prose, stores under each ctx key."""
    prose = {key: value for value, key in PROSE_WRITE.findall(text)}
    prose.update(dict(PROSE_SET.findall(text)))
    coded = {key: " ".join(value.split()) for key, value in CTX_WRITE.findall(text)}
    return {**prose, **coded}


def _text(step: Step) -> list[str]:
    return [option.code or option.spec for option in step.options]


def _names(value: str | None) -> list[str] | None:
    if value is None:
        return []
    try:
        parsed = ast.literal_eval(value.rstrip(")").strip())
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return None
    items = [parsed] if isinstance(parsed, str) else parsed
    if not isinstance(items, list | tuple) or not all(isinstance(i, str) for i in items):
        return None
    return list(items)


def _names_columns(values: list[str | None], columns: set[str]) -> bool:
    named = [_names(v) for v in values]
    if any(n is None for n in named):
        return False
    flat = [c for n in named if n for c in n]
    return bool(flat) and all(c in columns for c in flat)


def _varies(key: str, values: list[str | None]) -> bool:
    written = [v for v in values if v is not None] if key not in COLUMN_KEYS else values
    parsed = {repr(_names(v)) if _names(v) is not None else v for v in written}
    return len(parsed) > 1


def _columns(plan: AnalysisPlan) -> set[str]:
    created = {c for s in plan.steps for t in _text(s) for c in CREATED.findall(t)}
    return {c.name for c in plan.dataset.columns} | created


def varying_ctx_keys(plan: AnalysisPlan, step: Step) -> dict[str, str]:
    found: dict[str, str] = {}
    earlier = plan.steps[: next(i for i, s in enumerate(plan.steps) if s.id == step.id)]
    columns = _columns(plan)
    for index, writer in enumerate(earlier):
        writes = [ctx_writes(text) for text in _text(writer)]
        for key in set().union(*writes):
            values = [w.get(key) for w in writes]
            if not _varies(key, values) or (
                key not in COLUMN_KEYS and not _names_columns(values, columns)
            ):
                continue
            reader = ctx_read_pattern(key)
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
