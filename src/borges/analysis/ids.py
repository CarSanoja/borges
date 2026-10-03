from __future__ import annotations

import re

_NON_SLUG = re.compile(r"[^a-z0-9_]+")


def slug_id(raw: str) -> str:
    return _NON_SLUG.sub("_", raw.strip().lower()).strip("_")
