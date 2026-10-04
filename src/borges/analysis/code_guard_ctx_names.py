from __future__ import annotations

import ast
import re

from borges.analysis.code_guard_ctx import COLUMN_KEYS
from borges.analysis.models import Option, Step


def _named_in_spec(name: str, spec: str) -> bool:
    return re.search(rf"""ctx\s*\[\s*["']{re.escape(name)}["']""", spec) is not None


def _ctx_writes(tree: ast.AST) -> dict[str, list[ast.expr]]:
    writes: dict[str, list[ast.expr]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == "ctx"
                and isinstance(target.slice, ast.Constant)
                and isinstance(target.slice.value, str)
            ):
                writes.setdefault(target.slice.value, []).append(node.value)
    return writes


def ctx_name_violations(code: str, step: Step, option: Option) -> list[str]:
    """A ctx entry named after a column this step builds must hold that column's name.

    The keys that hold other columns' names by design (the covariate list, the outcome) and
    entries that hold a list of names are left alone."""
    names = [n for n in step.produces if n not in COLUMN_KEYS and _named_in_spec(n, option.spec)]
    if not names:
        return []
    try:
        writes = _ctx_writes(ast.parse(code))
    except SyntaxError:
        return []
    problems = []
    for name in names:
        values = writes.get(name, [])
        if values and all(isinstance(v, ast.Constant) and v.value == name for v in values):
            continue
        if values and all(isinstance(v, ast.List | ast.Tuple) for v in values):
            continue
        held = ast.unparse(values[0]) if values else "nothing"
        problems.append(
            f"the option stores its result in ctx['{name}'], which later steps read as a column "
            f"name (df[ctx['{name}']]), but this code puts {held} there; create the column "
            f"df['{name}'] and set ctx['{name}'] = '{name}'"
        )
    return problems
