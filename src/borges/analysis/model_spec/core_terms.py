from __future__ import annotations

WRAPPERS = ("C",)


def _words(name: str) -> set[str]:
    spaced = "".join(ch if ch.isalnum() or ch == "_" else " " for ch in name)
    return {t for t in spaced.split() if not t.isdigit()}


def is_core_term(name: str, core: list[str]) -> bool:
    if name in core:
        return True
    found = _words(name)
    return bool(found & set(core)) and found <= {*core, *WRAPPERS}


def runtime_filter_lines(core: list[str]) -> list[str]:
    return [
        f"    core_names = {core!r}",
        f"    allowed = {{*core_names, *{WRAPPERS!r}}}",
        "    words = lambda c: {",
        "        t",
        "        for t in ''.join(h if h.isalnum() or h in '_' else ' ' for h in c).split()",
        "        if not t.isdigit()",
        "    }",
        "    names = [",
        "        c",
        "        for c in dict.fromkeys(names)",
        "        if c not in core_names",
        "        and not (words(c) & set(core_names) and words(c) <= allowed)",
        "    ]",
    ]
