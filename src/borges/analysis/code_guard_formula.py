from __future__ import annotations

import re

from borges.analysis.code_guard_rules import (
    FORBIDDEN_MODULES,
    FORBIDDEN_NAMES,
    FORMULA_FUNCTIONS,
    FORMULA_NUMPY_FUNCTIONS,
)

DOTTED_IDENTIFIER = re.compile(r"[A-Za-z_]\w*\.[A-Za-z_]")
TOKEN = re.compile(
    r"\s*(?:(?P<number>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
    r"|(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<op>\*\*|[+\-*/:|(),=.]))"
)
INERT_LABELS = frozenset({"Pr(>|z|)", "Pr(>|t|)"})
LEVEL_LABEL = re.compile(r"\[(?:T\.)?[A-Za-z0-9_ .+\-]*\]")
INDEXED_TERM = (
    "a formula may not index a term; write C(x) in the formula "
    "and read the level coefficient as params['C(x)[T.level]']"
)
BINARY_OPERATORS = frozenset({"+", "-", "*", "/", ":", "**", "|"})


class FormulaError(ValueError):
    pass


def needs_formula_check(text: str) -> bool:
    if text in INERT_LABELS:
        return False
    return "(" in text or DOTTED_IDENTIFIER.search(text) is not None


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    position = 0
    stripped = text.rstrip()
    while position < len(stripped):
        match = TOKEN.match(stripped, position)
        if match is None:
            raise FormulaError(f"unsupported character {stripped[position:].lstrip()[:1]!r}")
        kind = match.lastgroup or ""
        tokens.append((kind, match.group(kind)))
        position = match.end()
    return tokens


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self.tokens = tokens
        self.index = 0

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self) -> tuple[str, str]:
        token = self.peek()
        if token is None:
            raise FormulaError("unexpected end of formula")
        self.index += 1
        return token

    def expect(self, value: str) -> None:
        token = self.take()
        if token[1] != value:
            raise FormulaError(f"expected '{value}' but found '{token[1]}'")

    def at_end(self) -> bool:
        return self.peek() is None

    def at(self, value: str) -> bool:
        token = self.peek()
        return token is not None and token[0] == "op" and token[1] == value

    def expression(self, allow_empty: bool = False) -> None:
        if allow_empty and (self.at_end() or self.at(")")):
            return
        self.unary()
        while True:
            token = self.peek()
            if token is None or token[0] != "op" or token[1] not in BINARY_OPERATORS:
                return
            self.index += 1
            self.unary()

    def unary(self) -> None:
        while self.at("+") or self.at("-"):
            self.index += 1
        self.primary()

    def primary(self) -> None:
        kind, value = self.take()
        if kind == "number":
            return
        if kind == "op" and value == "(":
            self.expression()
            self.expect(")")
            return
        if kind != "name":
            raise FormulaError(f"unexpected '{value}'")
        self.name_chain(value)

    def name_chain(self, first: str) -> None:
        chain = [first]
        while self.at("."):
            self.index += 1
            kind, value = self.take()
            if kind != "name":
                raise FormulaError(f"unexpected '{value}' after '.'")
            chain.append(value)
        called = self.at("(")
        dotted = ".".join(chain)
        if called:
            if dotted not in FORMULA_FUNCTIONS and not _numpy_function(chain):
                raise FormulaError(f"call to '{dotted}' is not an allowed formula function")
            self.index += 1
            self.arguments()
        elif len(chain) > 1:
            raise FormulaError(f"attribute chain '{dotted}' is not allowed")
        elif first in FORBIDDEN_NAMES or first in FORBIDDEN_MODULES:
            raise FormulaError(f"name '{first}' is not allowed")

    def arguments(self) -> None:
        while True:
            self.argument()
            if self.at(","):
                self.index += 1
                continue
            self.expect(")")
            return

    def argument(self) -> None:
        following = self.tokens[self.index + 1] if self.index + 1 < len(self.tokens) else None
        current = self.peek()
        if (
            current is not None
            and current[0] == "name"
            and following is not None
            and following[1] == "="
        ):
            self.index += 2
        self.expression()


def _numpy_function(chain: list[str]) -> bool:
    return len(chain) == 2 and chain[0] == "np" and chain[1] in FORMULA_NUMPY_FUNCTIONS


def formula_error(text: str) -> str | None:
    if "'" in text or '"' in text or "`" in text:
        return "formula-like strings may not contain quotes"
    if text.lstrip().startswith("("):
        return "formula-like strings may not start with a parenthesis"
    if "[" in text:
        if "~" in text:
            return INDEXED_TERM
        text = LEVEL_LABEL.sub("", text)
    try:
        for side in text.split("~"):
            parser = _Parser(_tokenize(side))
            parser.expression(allow_empty=True)
            if not parser.at_end():
                raise FormulaError(f"unexpected '{parser.take()[1]}'")
    except FormulaError as exc:
        return str(exc)
    return None
