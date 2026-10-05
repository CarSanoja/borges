"""Spec promises a feature option's code does not keep.

A checkout_ab option at 7ec07d9 had the spec "Set ctx['covariates'] to ['platform_ios',
'platform_android']" and code that built the dummies but never wrote ctx['covariates'], so the
model adjusted for nothing and the option was reported as a no-op. The same code renamed the
columns of get_dummies(drop_first=True) by position: the categories were android, ios and web, so
the columns it called platform_ios and platform_android held ios and web.
"""

from __future__ import annotations

import ast
import re

from borges.analysis.code_guard_ctx import COLUMN_KEYS, ctx_writes
from borges.analysis.models import Option, Step

SET_IN_SPEC = re.compile(
    r"""(?:\b(?:set|sets|setting|assign|assigns|store|stores|put|puts|write|writes|update|updates)"""
    r"""\s+(?:(?:to|into|in)\s+)?ctx\s*\[\s*["'](\w+)["']\s*\])"""
    r"""|(?:ctx\s*\[\s*["'](\w+)["']\s*\]\s*=(?!=))""",
    re.IGNORECASE,
)
MUTATORS = frozenset({"append", "extend", "insert", "update", "add"})


def _ctx_key(node: ast.AST) -> str | None:
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "ctx"
    ):
        key = node.slice
        return key.value if isinstance(key, ast.Constant) and isinstance(key.value, str) else "*"
    return None


def _written_keys(tree: ast.AST) -> set[str]:
    keys: set[str] = set()
    for node in ast.walk(tree):
        targets = node.targets if isinstance(node, ast.Assign) else []
        if isinstance(node, ast.AugAssign | ast.AnnAssign):
            targets = [node.target]
        keys.update(k for k in map(_ctx_key, targets) if k)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner, method = node.func.value, node.func.attr
            if (
                isinstance(owner, ast.Name)
                and owner.id == "ctx"
                and method in ("update", "setdefault")
            ):
                keys.add("*")
            key = _ctx_key(owner)
            if key and method in MUTATORS:
                keys.add(key)
    return keys


def spec_ctx_write_violations(code: str, spec: str) -> list[str]:
    """Only the keys later steps read from ctx (the covariate list and the outcome) are held to the
    spec; planners also write ctx['skin_tone'] for a column the step builds."""
    promised = sorted({a or b for a, b in SET_IN_SPEC.findall(spec)} & COLUMN_KEYS)
    if not promised:
        return []
    try:
        written = _written_keys(ast.parse(code))
    except SyntaxError:
        return []
    if "*" in written:
        return []
    return [
        f"the option's spec sets ctx['{key}'], but the code never writes ctx['{key}'], so later "
        f"steps do not see it; assign ctx['{key}'] as the spec says"
        for key in promised
        if key not in written
    ]


def _writes_outcome(option: Option) -> bool:
    if option.code is not None:
        try:
            return "outcome" in _written_keys(ast.parse(option.code))
        except SyntaxError:
            return False
    promised = {a or b for a, b in SET_IN_SPEC.findall(option.spec)}
    return "outcome" in promised or "outcome" in ctx_writes(option.spec)


def sibling_outcome_violations(code: str, step: Step, option: Option) -> list[str]:
    """A marp_norms step at 568a627 chose the outcome: 'Psychological well-being mean' wrote
    ctx['outcome'] and the default 'Overall well-being mean' only built a column, so the model fell
    back to wb_psych_mean and the headline estimate was fitted on the other outcome."""
    if not any(_writes_outcome(o) for o in step.options if o.id != option.id):
        return []
    try:
        written = _written_keys(ast.parse(code))
    except SyntaxError:
        return []
    if written & {"*", "outcome"}:
        return []
    return [
        "the other options of this step write ctx['outcome'], which later steps read; write "
        "ctx['outcome'] here too, with the outcome column this option uses, or a later step falls "
        "back to another option's outcome"
    ]


def _dummy_frames(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "get_dummies"
        ):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def positional_dummy_violations(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    frames = _dummy_frames(tree)
    problems = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.List | ast.Tuple):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "columns"
                and isinstance(target.value, ast.Name)
                and target.value.id in frames
            ):
                problems.append(
                    f"line {node.lineno}: the columns of get_dummies are renamed by position, "
                    "which depends on the order of the categories and on drop_first; use "
                    "prefix= and pick the dummy columns by name"
                )
    return problems
