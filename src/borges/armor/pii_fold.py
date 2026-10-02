from __future__ import annotations

import unicodedata

KEEP_CONTROLS = frozenset("\n\t\r")
SPACE_CATEGORY = "Zs"
DROPPED_CATEGORIES = frozenset({"Cf", "Cc", "Co", "Cs"})


def fold_with_map(text: str) -> tuple[str, list[int]]:
    """Fold look-alike characters away so detectors see plain text; map each folded char back."""
    folded: list[str] = []
    origin: list[int] = []
    for position, char in enumerate(text):
        category = unicodedata.category(char)
        if category in DROPPED_CATEGORIES and char not in KEEP_CONTROLS:
            continue
        if category == SPACE_CATEGORY:
            folded.append(" ")
            origin.append(position)
            continue
        for piece in unicodedata.normalize("NFKC", char):
            folded.append(piece)
            origin.append(position)
    return "".join(folded), origin
