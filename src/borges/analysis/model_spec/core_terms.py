from __future__ import annotations

WRAPPERS = ("C",)
OPERATORS = " :*+()"


def _words(name: str) -> set[str]:
    spaced = "".join(ch if ch.isalnum() or ch == "_" else " " for ch in name)
    return {t for t in spaced.split() if not t.isdigit()}


def _plain_operators(name: str) -> bool:
    rest = "".join(ch for ch in name if not (ch.isalnum() or ch == "_"))
    return set(rest) <= set(OPERATORS) and "**" not in name


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
        "    plain = lambda c: set(''.join(h for h in c if not (h.isalnum() or h == '_'))) <= "
        f"set({OPERATORS!r}) and '**' not in c",
        "    names = [",
        "        c",
        "        for c in dict.fromkeys(names)",
        "        if c not in core_names",
        "        and not (words(c) & set(core_names) and words(c) <= allowed and plain(c))",
        "    ]",
    ]
