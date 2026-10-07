"""A ctx key that holds a column name, used as if it held the column's values.

fertility_vote on 7 October: in run 18 the cycle-day step computed df['DateTesting'] -
ctx['next_onset'], a date column minus the string 'next_onset', and in run 21 the window step
compared ctx['cycle_day'] with 7; both failed their smoke runs, the user's own options were
dropped, and the starting point became a changed analysis. Arithmetic on such a key, or a
comparison with a number or with a string that is not a column, is refused before the code runs.
"""

from __future__ import annotations

import ast
import re

from borges.analysis.code_guard_ctx import _columns, ctx_writes
from borges.analysis.models import AnalysisPlan, Step

MESSAGE = (
    "ctx['{key}'] holds the column name '{name}', not its values, but this code uses it in "
    "arithmetic or a comparison; read the column as df[ctx['{key}']]"
)


def _named_columns(plan: AnalysisPlan, step: Step) -> dict[str, str]:
    """ctx keys that the earlier steps set to one column name."""
    index = next((i for i, s in enumerate(plan.steps) if s.id == step.id), 0)
    found: dict[str, str] = {}
    for earlier in plan.steps[:index]:
        for option in earlier.options:
            for key, value in ctx_writes(option.code or option.spec).items():
                text = value.strip().rstrip(".").strip()
                if len(text) > 2 and text[0] == text[-1] and text[0] in "'\"":
                    name = text[1:-1]
                    if name.replace("_", "").isalnum():
                        found.setdefault(key, name)
    return found


def _constant(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _strings(text: str) -> set[str]:
    found: set[str] = set()
    for value in ctx_writes(text).values():
        found.update(re.findall(r"""["'](\w+)["']""", value))
    return found


def _key(node: ast.AST) -> str | None:
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "ctx"
    ):
        return _constant(node.slice)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "ctx"
        and node.func.attr == "get"
        and node.args
    ):
        return _constant(node.args[0])
    return None


def _textual(node: ast.AST, names: set[str], strict: bool) -> bool:
    """Whether the other side is text: any string joins a name, but only a column name is
    compared with one."""
    if isinstance(node, ast.JoinedStr | ast.Name) or _key(node) is not None:
        return True
    text = _constant(node)
    if text is None:
        return False
    return not strict or text in names


def _misused(tree: ast.AST, keys: dict[str, str], columns: set[str]) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        pairs: list[tuple[ast.AST, ast.AST]] = []
        if isinstance(node, ast.BinOp):
            pairs = [(node.left, node.right), (node.right, node.left)]
        elif isinstance(node, ast.Compare) and len(node.comparators) == 1:
            if isinstance(node.ops[0], ast.In | ast.NotIn):
                continue
            pairs = [(node.left, node.comparators[0]), (node.comparators[0], node.left)]
        for side, other in pairs:
            key = _key(side)
            if key is None or key not in keys:
                continue
            joined = isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)
            compared = isinstance(node, ast.Compare)
            if (joined or compared) and _textual(other, columns, strict=compared):
                continue
            found.append(key)
    return sorted(set(found))


def ctx_value_violations(code: str, plan: AnalysisPlan, step: Step) -> list[str]:
    keys = _named_columns(plan, step)
    if not keys:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    written = {v for s in plan.steps for o in s.options for v in _strings(o.code or o.spec)}
    columns = _columns(plan) | set(keys.values()) | written
    return [MESSAGE.format(key=k, name=keys[k]) for k in _misused(tree, keys, columns)]
