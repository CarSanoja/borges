from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

Action = Literal["refuse", "quarantine", "redact", "drop", "block"]
MEMORY_FIELD = "memory:"
Kind = Literal["injection", "tool_poisoning", "pii"]

ARMOR_PRINCIPAL = "armor://borges/screen"
QUARANTINE_TOKEN = "[quarantined: instruction-like text]"


@dataclass(frozen=True)
class ArmorDecision:
    action: Action
    kind: Kind
    field: str
    detail: str
    count: int = 1
    quote: str = ""

    @property
    def denies(self) -> bool:
        return self.action != "redact"


@dataclass
class ArmorReport:
    decisions: list[ArmorDecision] = field(default_factory=list)

    def add(self, decision: ArmorDecision) -> None:
        self.decisions.append(decision)

    def extend(self, other: ArmorReport) -> None:
        self.decisions.extend(other.decisions)

    def __bool__(self) -> bool:
        return bool(self.decisions)

    def of(self, action: Action) -> list[ArmorDecision]:
        return [d for d in self.decisions if d.action == action]

    def pii_counts(self) -> Counter[str]:
        counts: Counter[str] = Counter()
        for decision in self.decisions:
            if decision.kind == "pii":
                counts[decision.detail] += decision.count
        return counts

    def caveats(self) -> list[str]:
        lines: list[str] = []
        quarantined = self.of("quarantine")
        if quarantined:
            fields = ", ".join(sorted({d.field for d in quarantined})[:6])
            lines.append(
                f"Armor quarantined {len(quarantined)} instruction-like text(s) before any model "
                f"saw them ({fields}); their content was replaced by a redacted token and "
                "never used."
            )
        counts = self.pii_counts()
        if counts:
            kinds = ", ".join(f"{kind} x{n}" for kind, n in sorted(counts.items()))
            lines.append(
                f"Armor redacted personal data from what models saw ({kinds}); "
                "the analysis code still reads the raw columns."
            )
        dropped = self.of("drop")
        remembered = [d for d in dropped if d.field.startswith(MEMORY_FIELD)]
        options = len(dropped) - len(remembered)
        if options:
            lines.append(
                f"Armor dropped {options} model-proposed option(s) that tried to steer "
                "the result or the code."
            )
        if remembered:
            lines.append(
                f"Armor kept {len(remembered)} remembered entr"
                f"{'y' if len(remembered) == 1 else 'ies'} from earlier runs out of every prompt "
                "because they read as steering the result or the code; this run's own options "
                "were not affected."
            )
        return lines
