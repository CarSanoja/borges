"""Internal option and step ids in a summary.

A marp_norms summary at 9b95d04 wrote "Adding country fixed effects (opt_adj_full_demo)", a
shortened form of the adversary's option id, and a marp_religiosity one at 508fe2e named the
flipped universe "(u_c8af06a403)"; a hurricanes one at a491fe1 wrote "(u_12c11039f3, estimate
3.74, ...)". A universe id is dropped wherever it stands, and a parenthesised token that is, or is
part of, an option or step id is dropped; an exact id elsewhere becomes the option's label or the
step's title.
"""

from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan

PAREN = re.compile(r"\s*\(\s*([A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+)\s*\)")
TOKEN = re.compile(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b")
MIN_PART = 6
UNIVERSE = re.compile(r"u_[0-9a-f]{10}")
LEADING_UNIVERSE = re.compile(r"\(\s*u_[0-9a-f]{10}\s*[,;:]\s*")
BARE_UNIVERSE = re.compile(r"\s+u_[0-9a-f]{10}\b")


def _names(plan: AnalysisPlan) -> dict[str, str]:
    names = {s.id: s.title for s in plan.steps}
    names.update({o.id: f'"{o.label}"' for s in plan.steps for o in s.options})
    return names


def drop_option_ids(plan: AnalysisPlan, narrative: str) -> str:
    names = _names(plan)

    def internal(token: str) -> bool:
        if UNIVERSE.fullmatch(token):
            return True
        return token in names or (len(token) >= MIN_PART and any(token in i for i in names))

    text = PAREN.sub(lambda m: "" if internal(m.group(1)) else m.group(0), narrative)
    text = BARE_UNIVERSE.sub("", LEADING_UNIVERSE.sub("(", text))
    return TOKEN.sub(lambda m: names.get(m.group(0), m.group(0)), text)
