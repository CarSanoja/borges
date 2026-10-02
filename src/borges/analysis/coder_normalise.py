from __future__ import annotations

import ast

CLOSERS = frozenset("}])")


def _parses(code: str) -> bool:
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    return True


def strip_trailing_closer(code: str) -> tuple[str, bool]:
    if _parses(code):
        return code, False
    lines = code.rstrip().split("\n")
    last = lines[-1].strip()
    if not last or any(char not in CLOSERS for char in last):
        return code, False
    trimmed = "\n".join(lines[:-1]).rstrip() + "\n"
    if not _parses(trimmed):
        return code, False
    return trimmed, True
