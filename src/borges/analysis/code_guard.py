from __future__ import annotations

import ast

from borges.analysis.models import StepKind

ALLOWED_IMPORTS = frozenset(
    {
        "pandas",
        "numpy",
        "math",
        "scipy",
        "scipy.stats",
        "statsmodels",
        "statsmodels.api",
        "statsmodels.formula.api",
    }
)

FORBIDDEN_NAMES = frozenset(
    {
        "eval",
        "exec",
        "open",
        "compile",
        "__import__",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
        "input",
        "breakpoint",
        "exit",
        "quit",
        "SystemExit",
        "KeyboardInterrupt",
        "BaseException",
    }
)

FORBIDDEN_MODULES = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "shutil",
        "pathlib",
        "requests",
        "urllib",
        "importlib",
        "pickle",
        "io",
        "builtins",
    }
)

FORBIDDEN_ATTRIBUTES = frozenset(
    {
        "load",
        "loads",
        "save",
        "savez",
        "savetxt",
        "loadtxt",
        "genfromtxt",
        "fromfile",
        "fromregex",
        "tofile",
        "open",
        "memmap",
        "DataSource",
        "lib",
        "ctypeslib",
        "f2py",
        "system",
        "popen",
        "eval",
        "query",
        "format",
        "format_map",
        "dump",
        "dumps",
        "save_npz",
        "load_npz",
        "datasets",
        "iolib",
        "HDFStore",
        "ExcelFile",
        "ExcelWriter",
        "get_rdataset",
        "webuse",
    }
)

ALLOWED_TO_ATTRIBUTES = frozenset(
    {
        "to_numpy",
        "to_dict",
        "to_list",
        "to_frame",
        "to_numeric",
        "to_datetime",
        "to_timedelta",
        "to_string",
    }
)

EXPECTED_PARAMS = ["df", "ctx"]


def _module_allowed(module: str) -> bool:
    return module in ALLOWED_IMPORTS


def _imported_name_violation(name: str) -> str | None:
    if name == "*":
        return "star imports are not allowed"
    if name.startswith("__") and name.endswith("__"):
        return f"dunder name '{name}' is not allowed"
    if name in FORBIDDEN_NAMES or name in FORBIDDEN_MODULES or name in FORBIDDEN_ATTRIBUTES:
        return f"import of name '{name}' is not allowed"
    if name.startswith(("read_", "to_")) and name not in ALLOWED_TO_ATTRIBUTES:
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
    if attr.startswith(("read_", "to_")) and attr not in ALLOWED_TO_ATTRIBUTES:
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
    if isinstance(node.value, str) and ("__" in node.value or "@" in node.value):
        return [f"line {node.lineno}: string constants may not contain '__' or '@'"]
    return []


def _body_violations(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Import | ast.ImportFrom):
            violations.extend(_import_violations(node))
        elif isinstance(node, ast.Attribute):
            violations.extend(_attribute_violations(node))
        elif isinstance(node, ast.Name):
            violations.extend(_name_violations(node))
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
