from __future__ import annotations

import re

from borges.analysis.path_scrub import scrub_paths

SECRET = re.compile(
    r"(?i)\b(?:sk|nvapi|csk|ctr|ghp|xox[bap])[-_][A-Za-z0-9_\-]{8,}"
    r"|\bbearer\s+[A-Za-z0-9._\-]{8,}"
    r"|\b[A-Za-z0-9_\-]{40,}\b"
)
REDACTED = "[redacted]"


def redact_text(value: object, limit: int | None = None) -> str:
    text = SECRET.sub(REDACTED, scrub_paths(str(value)))
    return text[:limit] if limit is not None else text
