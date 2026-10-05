"""Whether a filter option says it keeps every row.

The checkout default at 508fe2e, "Keep all sessions: return the input DataFrame unchanged; no rows
are dropped", dropped internal and short sessions unless ctx['keep_all'] was set: 1,255 of 29,926
rows. The alternatives then looked as if they re-included invalid rows. A filter option whose own
words keep every row must return as many rows as it received.
"""

from __future__ import annotations

import re

from borges.analysis.model_spec.interaction import own_text
from borges.analysis.models import Option, Step

KEEP = re.compile(
    r"\bkeep(?:s|ing)? (?:all|every)\b(?! (?:columns?|variables?|covariates?|features?|items?)\b)|"
    r"\bno rows? (?:is|are) (?:dropped|removed|excluded)\b|"
    r"\breturn (?:the )?(?:input )?(?:data ?frame|data|df) unchanged\b",
    re.IGNORECASE,
)
EXCEPT = re.compile(r"\b(?:except|other than|apart from|but (?:drop|exclude|remove))\b", re.I)


def keeps_rows(step: Step, option: Option) -> bool:
    text = own_text(option)
    return step.kind == "filter" and KEEP.search(text) is not None and not EXCEPT.search(text)


GROUP = re.compile(r"\bgroup(?:ed|s)? by [`'\"]?([A-Za-z_]\w*)", re.IGNORECASE)


def grouped_by(step: Step, option: Option) -> str | None:
    """The checkout aggregation at 95200c8, "Group by user_id; compute variant as the first variant
    per user", was coded as if apply() received one user's rows: it returned a single row, the
    first session's variant, and every model option then failed on a one-level exposure. An option
    that groups by a column must return one row per distinct value of it."""
    if step.kind not in {"transform", "feature"}:
        return None
    match = GROUP.search(own_text(option))
    return match.group(1) if match else None
