from __future__ import annotations

from dataclasses import dataclass

QUOTE_CHARS = 60


@dataclass(frozen=True)
class Finding:
    category: str
    pattern: str
    technique: str
    quote: str

    def describe(self) -> str:
        return f"{self.category} ({self.technique})"


def clip(text: str, limit: int = QUOTE_CHARS) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"
