from __future__ import annotations

import ast
import re
from functools import cache

from borges.analysis.harness import POLICY_CALL, POLICY_SOURCE
from borges.analysis.harness_main import MAIN_TEMPLATE

_PLACEHOLDERS = re.compile(r"__[A-Z][A-Z_]*__")
_PRELUDE_LINE = re.compile(
    r"exec\(compile\((?P<literal>'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"), "
    r"'<borges-policy>', 'exec'\), \{\}\)\n"
)
_ARGUMENT = r"(?:None|'(?:[^'\\\n]|\\.)*')"


@cache
def _main_pattern() -> re.Pattern[str]:
    parts = _PLACEHOLDERS.split(MAIN_TEMPLATE)
    return re.compile("\n" + "[^\n]*".join(re.escape(part) for part in parts))


@cache
def _policy_pattern() -> re.Pattern[str]:
    head, tail = POLICY_SOURCE.split(POLICY_CALL)
    call = rf"_borges_install_policy\({_ARGUMENT}, {_ARGUMENT}\)"
    return re.compile(re.escape(head) + call + re.escape(tail))


def _prelude_is_genuine(prefix: str) -> bool:
    matched = _PRELUDE_LINE.fullmatch(prefix)
    if matched is None:
        return False
    try:
        source = ast.literal_eval(matched.group("literal"))
    except (ValueError, SyntaxError):
        return False
    return isinstance(source, str) and _policy_pattern().fullmatch(source) is not None


def is_rendered_step(text: str, body: str) -> bool:
    """True when text is exactly the harness prelude, this code body and the harness main."""
    start = text.find(body)
    while start >= 0:
        end = start + len(body)
        if _prelude_is_genuine(text[:start]) and _main_pattern().fullmatch(text, end):
            return True
        start = text.find(body, start + 1)
    return False
