from __future__ import annotations

import ast
import re

from borges.analysis.code_guard_introspection import (
    attribute_violations as introspection_attribute_violations,
)
from borges.analysis.code_guard_introspection import (
    name_violations as introspection_name_violations,
)
from borges.analysis.code_guard_introspection import subscript_violations
from borges.analysis.code_guard_rules import (
    ALLOWED_IMPORTS,
    ALLOWED_TO_ATTRIBUTES,
    FORBIDDEN_ATTRIBUTES,
    FORBIDDEN_MODULES,
    FORBIDDEN_NAMES,
    FORMULA_CALLS,
    IO_PREFIXES,
)
from borges.analysis.models import StepKind

EXPECTED_PARAMS = ["df", "ctx"]
CALL_PATTERN = re.compile(r"([A-Za-z_][\w.]*)\s*\(")


def _module_allowed(module: str) -> bool:
    return module in ALLOWED_IMPORTS


def _imported_name_violation(name: str) -> str | None:
    if name == "*":
        return "star imports are not allowed"
    if name.startswith("__") and name.endswith("__"):
        return f"dunder name '{name}' is not allowed"
    if name in FORBIDDEN_NAMES or name in FORBIDDEN_MODULES or name in FORBIDDEN_ATTRIBUTES:
        return f"import of name '{name}' is not allowed"
    if name.startswith(IO_PREFIXES) and name not in ALLOWED_TO_ATTRIBUTES:
        return f"import of I/O name '{name}' is not allowed"
    return None


def _import_violations(node: ast.Import | ast.ImportFrom) -> list[str]:
    where = f"line {node.lineno}"
    if isinstance(node, ast.Import):
        return [
            f"{where}: import of '{alias.name}' is not allowed"
            for alias in node.names
            if not _module_allowed(alias.name)
        ]
    if node.level > 0 or node.module is None:
        return [f"{where}: relative imports are not allowed"]
    violations = []
    if not _module_allowed(node.module):
        violations.append(f"{where}: import of '{node.module}' is not allowed")
    for alias in node.names:
        reason = _imported_name_violation(alias.name)
        if reason:
            violations.append(f"{where}: {reason}")
    return violations


def _attribute_violations(node: ast.Attribute) -> list[str]:
    attr = node.attr
    where = f"line {node.lineno}"
    if attr.startswith("__") and attr.endswith("__"):
        return [f"{where}: dunder attribute '{attr}' is not allowed"]
    if attr in FORBIDDEN_MODULES or attr in FORBIDDEN_ATTRIBUTES:
        return [f"{where}: attribute '{attr}' is not allowed"]
    if attr.startswith(IO_PREFIXES) and attr not in ALLOWED_TO_ATTRIBUTES:
        return [f"{where}: I/O attribute '{attr}' is not allowed"]
    return []


def _name_violations(node: ast.Name) -> list[str]:
    name = node.id
    where = f"line {node.lineno}"
    if name.startswith("__") and name.endswith("__"):
        return [f"{where}: dunder name '{name}' is not allowed"]
    if name in FORBIDDEN_NAMES:
        return [f"{where}: use of '{name}' is not allowed"]
    if name in FORBIDDEN_MODULES:
        return [f"{where}: use of module '{name}' is not allowed"]
    return []


def _constant_violations(node: ast.Constant) -> list[str]:
    if not isinstance(node.value, str):
        return []
    if "__" in node.value or "@" in node.value:
        return [f"line {node.lineno}: string constants may not contain '__' or '@'"]
    return _formula_violations(node)


def _formula_violations(node: ast.Constant) -> list[str]:
    text = node.value
    where = f"line {node.lineno}"
    calls = CALL_PATTERN.findall(text)
    if "~" in text:
        if "'" in text or '"' in text or "`" in text:
            return [f"{where}: formula strings may not contain quotes"]
        bad = [name for name in calls if name not in FORMULA_CALLS]
    else:
        bad = [name for name in calls if name.split(".")[-1] in FORBIDDEN_NAMES]
    if bad:
        return [f"{where}: string constants may not call '{bad[0]}'"]
    return []


def _body_violations(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Import | ast.ImportFrom):
            violations.extend(_import_violations(node))
        elif isinstance(node, ast.Attribute):
            violations.extend(_attribute_violations(node))
            violations.extend(introspection_attribute_violations(node))
        elif isinstance(node, ast.Name):
            violations.extend(_name_violations(node))
            violations.extend(introspection_name_violations(node))
        elif isinstance(node, ast.Subscript):
            violations.extend(subscript_violations(node))
        elif isinstance(node, ast.Constant):
            violations.extend(_constant_violations(node))
    return violations


def _signature_violations(func: ast.FunctionDef | ast.AsyncFunctionDef, expected: str) -> list[str]:
    violations: list[str] = []
    if isinstance(func, ast.AsyncFunctionDef):
        violations.append(f"function '{expected}' must not be async")
    args = func.args
    positional = [a.arg for a in args.posonlyargs + args.args]
    if positional != EXPECTED_PARAMS or args.vararg or args.kwarg or args.kwonlyargs:
        violations.append(f"function '{expected}' must have exactly the parameters (df, ctx)")
    return violations


def _is_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def check_code(code: str, kind: StepKind) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"syntax error at line {exc.lineno}: {exc.msg}"]
    expected = "estimate" if kind == "model" else "apply"
    violations: list[str] = []
    funcs: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for index, node in enumerate(tree.body):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            funcs.append(node)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            violations.extend(_import_violations(node))
        elif index == 0 and _is_docstring(node):
            continue
        else:
            violations.append(
                f"line {node.lineno}: top level may only contain imports, a docstring and "
                f"the '{expected}' function"
            )
    if len(funcs) != 1:
        violations.append(f"code must define exactly one top-level function '{expected}'")
        return violations
    func = funcs[0]
    if func.name != expected:
        violations.append(f"the function must be named '{expected}', found '{func.name}'")
    violations.extend(_signature_violations(func, func.name))
    violations.extend(_body_violations(func))
    return violations
