"""Intervals at another level than the 95% the result reports.

A red_cards baseline at 1ecb614 called res.conf_int(alpha=0.025) and reported the 97.5% interval as
ci_low and ci_high: the report printed "95% CI 0.99 to 1.68" beside p = 0.031. Among 365 conf_int
calls in the recorded model code, two passed an alpha other than 0.05, both this mistake.
"""

from __future__ import annotations

import ast

LEVEL_CALLS = frozenset({"conf_int", "summary_frame"})


def _alpha(node: ast.Call) -> ast.expr | None:
    found = next((k.value for k in node.keywords if k.arg == "alpha"), None)
    if found is None and isinstance(node.func, ast.Attribute) and node.func.attr == "conf_int":
        found = node.args[0] if node.args else None
    return found


def interval_level_violations(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr not in LEVEL_CALLS:
            continue
        alpha = _alpha(node)
        if not isinstance(alpha, ast.Constant) or not isinstance(alpha.value, int | float):
            continue
        if abs(float(alpha.value) - 0.05) < 1e-12:
            continue
        level = 100 * (1 - float(alpha.value))
        found.append(
            f"line {node.lineno}: {ast.unparse(node)[:60]} gives a {level:g}% interval, but "
            "ci_low and ci_high are the 95% interval; use alpha=0.05"
        )
    return found
