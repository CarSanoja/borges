from __future__ import annotations

from borges.armor.report import ArmorDecision


class ArmorRefusal(ValueError):
    """Raised when untrusted run input carries instruction-like text; maps to HTTP 400."""

    def __init__(self, decisions: list[ArmorDecision]) -> None:
        self.decisions = decisions
        fields = ", ".join(sorted({d.field for d in decisions}))
        kinds = ", ".join(sorted({d.detail for d in decisions}))
        super().__init__(
            f"Armor refused the run: {fields} contains instruction-like text ({kinds}). "
            "Remove the instruction and submit again."
        )
