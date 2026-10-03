from __future__ import annotations

import ast
import re

from borges.analysis.models import Option, Step
from borges.analysis.option_signature import same_option

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "to",
        "as",
        "in",
        "on",
        "for",
        "by",
        "with",
        "and",
        "or",
        "use",
        "using",
        "used",
        "treat",
        "treating",
        "keep",
        "apply",
        "applied",
        "model",
        "variable",
        "variables",
        "column",
        "columns",
        "all",
        "same",
        "standard",
        "default",
        "baseline",
        "conventional",
        "approach",
        "option",
        "analysis",
    }
)
TOKEN = re.compile(r"[a-z0-9]+")
MIN_TOKENS = 2


def _stem(token: str) -> str:
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(option: Option) -> frozenset[str]:
    words = TOKEN.findall(f"{option.label} {option.spec}".lower())
    return frozenset(_stem(w) for w in words if w not in STOPWORDS)


class _Canonical(ast.NodeTransformer):
    def __init__(self) -> None:
        self.names: dict[str, str] = {}

    def _alias(self, name: str) -> str:
        return self.names.setdefault(name, f"v{len(self.names)}")

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id in ("df", "ctx", "np", "pd", "sm", "smf", "stats"):
            return node
        return ast.copy_location(ast.Name(id=self._alias(node.id), ctx=node.ctx), node)

    def visit_arg(self, node: ast.arg) -> ast.AST:
        if node.arg in ("df", "ctx"):
            return node
        return ast.copy_location(ast.arg(arg=self._alias(node.arg)), node)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, str):
            collapsed = re.sub(r"\s+", " ", node.value.strip().lower())
            return ast.copy_location(ast.Constant(value=collapsed), node)
        return node


def _code_signature(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            node.name = "f"
            node.body = [
                n
                for n in node.body
                if not (
                    isinstance(n, ast.Expr)
                    and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, str)
                )
            ]
    canonical = _Canonical().visit(tree)
    return ast.dump(canonical, annotate_fields=False, include_attributes=False)


def equivalence_reason(step: Step, option: Option) -> str | None:
    default = step.default
    if option.id == default.id or option.is_default:
        return None
    if option.code and default.code:
        mine, theirs = _code_signature(option.code), _code_signature(default.code)
        if mine is not None and mine == theirs:
            return (
                f"same estimator, covariates and sample filter as the conventional option "
                f"'{default.id}' after normalising the code"
            )
    if same_option(option, default):
        return f"the same option as the conventional '{default.id}' under another name"
    mine_tokens, theirs_tokens = _tokens(option), _tokens(default)
    if len(mine_tokens) >= MIN_TOKENS and mine_tokens == theirs_tokens:
        return (
            f"the description names the same method and variables as the conventional "
            f"option '{default.id}'"
        )
    return None
