from __future__ import annotations

import re

from borges.armor.normalize import canonical

MIN_CHARS = 24
WEAK_SIGNALS = (
    r"\b(?:you|assistant|model|analyst|llm|ai|agent|tu|usted|asistente|modelo|analista)\b"
    r".{0,30}\b(?:must|should|need\s+to|have\s+to|shall|will|debes?|tienes\s+que|deberia)\b",
    r"\b(?:instead|rather\s+than|disregard|override|always|never|siempre|nunca|en\s+lugar)\b",
    r"\b(?:note\s+to|attention|important|urgent|nota\s+para|atencion|importante|urgente)\s*[:!]",
    r"\b(?:conclude|report|answer|respond|recommend|decide|concluye|reporta|responde)\b",
    r"\b(?:do\s+not|don'?t|never|no)\s+(?:use|include|consider|mention|usar|incluir|considerar)\b",
)
_WEAK = tuple(re.compile(p, re.IGNORECASE | re.DOTALL) for p in WEAK_SIGNALS)


def is_ambiguous(text: str) -> bool:
    if len(text) < MIN_CHARS:
        return False
    folded = canonical(text)
    return any(pattern.search(folded) for pattern in _WEAK)
