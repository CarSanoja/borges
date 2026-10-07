from __future__ import annotations

WRAPPERS = ("C",)
PLAIN_SYMBOLS = "_ :*+"
PARENTHESES = (40, 41)


def _words(name: str) -> set[str]:
    spaced = "".join(ch if ch.isalnum() or ch == "_" else " " for ch in name)
    return {t for t in spaced.split() if not t.isdigit()}


def _plain_operators(name: str) -> bool:
    plain = (ch.isalnum() or ch in PLAIN_SYMBOLS or ord(ch) in PARENTHESES for ch in name)
    return all(plain) and "**" not in name


def is_core_term(name: str, core: list[str]) -> bool:
    """A covariate the design already holds: a core column, or a product, sum or C() of core
    columns. Any other operator (x**2, x/m, x-m) makes a new term, which is kept."""
    if name in core:
        return True
    found = _words(name)
    return bool(found & set(core)) and found <= {*core, *WRAPPERS} and _plain_operators(name)


def runtime_filter_lines(core: list[str]) -> list[str]:
    return [
        f"    core_names = {core!r}",
        f"    allowed = {{*core_names, *{WRAPPERS!r}}}",
        "    words = lambda c: {",
        "        t",
        "        for t in ''.join(h if h.isalnum() or h in '_' else ' ' for h in c).split()",
        "        if not t.isdigit()",
        "    }",
        "    plain = lambda c: '**' not in c and all(",
        f"        h.isalnum() or h in {PLAIN_SYMBOLS!r} or ord(h) in {PARENTHESES!r} for h in c",
        "    )",
        "    names = [",
        "        c",
        "        for c in dict.fromkeys(names)",
        "        if c not in core_names",
        "        and not (words(c) & set(core_names) and words(c) <= allowed and plain(c))",
        "    ]",
    ]
