from __future__ import annotations

import re

from borges.analysis.models import Option

NON_ALNUM = re.compile(r"[^a-z0-9]+")
ID_PREFIXES = ("adv_", "alt_", "opt_")


def normalise_text(text: str) -> str:
    return NON_ALNUM.sub(" ", text.lower()).strip()


def strip_id_prefixes(option_id: str) -> str:
    stripped = option_id.lower()
    changed = True
    while changed:
        changed = False
        for prefix in ID_PREFIXES:
            if stripped.startswith(prefix) and len(stripped) > len(prefix):
                stripped = stripped[len(prefix) :]
                changed = True
    return stripped


def _contained(a: str, b: str) -> bool:
    return bool(a) and bool(b) and (a in b or b in a)


def same_option(a: Option, b: Option) -> bool:
    label_a, label_b = normalise_text(a.label), normalise_text(b.label)
    spec_a, spec_b = normalise_text(a.spec), normalise_text(b.spec)
    if label_a and label_a == label_b:
        return True
    if spec_a and spec_a == spec_b:
        return True
    if strip_id_prefixes(a.id) != strip_id_prefixes(b.id):
        return False
    return _contained(label_a, label_b) or _contained(spec_a, spec_b)
