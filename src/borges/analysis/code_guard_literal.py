from __future__ import annotations

import ast

RESULT_KEYS = frozenset({"estimate", "ci_low", "ci_high", "p_value", "se"})
BOUND_NAMES = frozenset({"ci_low", "ci_high", "lower", "upper", "lo", "hi", "low", "high"})
CASTS = frozenset({"float", "int"})


def _unwrap(value: ast.expr) -> ast.expr:
    while isinstance(value, ast.Call) and getattr(value.func, "id", None) in CASTS and value.args:
        value = value.args[0]
    return value.operand if isinstance(value, ast.UnaryOp) else value


def _number(value: ast.expr) -> bool:
    value = _unwrap(value)
    if not isinstance(value, ast.Constant):
        return False
    return isinstance(value.value, int | float) and not isinstance(value.value, bool)


def _name(value: ast.expr) -> str | None:
    value = _unwrap(value)
    return value.id if isinstance(value, ast.Name) else None


BRANCHES = (ast.If, ast.Try, ast.ExceptHandler, ast.For, ast.While, ast.With)


def _blocks(tree: ast.AST) -> list[list[ast.stmt]]:
    """Statement lists inside a branch, a handler or a loop: the places a fallback hides."""
    blocks: list[list[ast.stmt]] = []
    for node in ast.walk(tree):
        if not isinstance(node, BRANCHES):
            continue
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if isinstance(block, list) and block and isinstance(block[0], ast.stmt):
                blocks.append(block)
    return blocks


def _result_items(statement: ast.Return) -> list[tuple[str, ast.expr]]:
    if not isinstance(statement.value, ast.Dict):
        return []
    return [
        (key.value, value)
        for key, value in zip(statement.value.keys, statement.value.values, strict=True)
        if isinstance(key, ast.Constant) and key.value in RESULT_KEYS
    ]


def _fixed_returns(block: list[ast.stmt]) -> list[str]:
    fixed: dict[str, bool] = {}
    found: list[str] = []
    for statement in block:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    fixed[target.id] = _number(statement.value)
        if isinstance(statement, ast.Return):
            found.extend(
                f"line {statement.lineno}: the result returns a fixed {key} "
                f"({ast.unparse(value)}), which invents a result; when the model cannot be "
                "estimated, raise a ValueError so the option fails visibly"
                for key, value in _result_items(statement)
                if _number(value) or fixed.get(_name(value) or "", False)
            )
    return found


def literal_result_violations(tree: ast.AST) -> list[str]:
    """fertility_religiosity, 6 October 2026: after a rank-deficient fit, a runtime repair
    returned estimate 0, interval [-0.1, 0.1] and p 1 whenever the exposure did not vary, and the
    run reported that made-up null as its original verdict."""
    return [problem for block in _blocks(tree) for problem in _fixed_returns(block)]


def _shifted(target: ast.expr, value: ast.expr) -> bool:
    if not (isinstance(target, ast.Name) and target.id in BOUND_NAMES):
        return False
    if not (isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add | ast.Sub)):
        return False
    return _name(value.left) == target.id and _number(value.right)


def widened_interval_violations(tree: ast.AST) -> list[str]:
    """The same repair widened a degenerate interval by 0.05 on each side."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            hit = _shifted(node.targets[0], node.value)
        elif isinstance(node, ast.AugAssign):
            hit = isinstance(node.op, ast.Add | ast.Sub) and _shifted(
                node.target, ast.BinOp(left=node.target, op=node.op, right=node.value)
            )
        else:
            hit = False
        if hit:
            found.append(
                f"line {node.lineno}: {ast.unparse(node)} moves an interval bound by a fixed "
                "amount, which invents precision or uncertainty; report the interval the model "
                "gives, or raise a ValueError when it is degenerate"
            )
    return found
