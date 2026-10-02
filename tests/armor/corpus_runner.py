from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from borges.armor.injection import MODEL_OUTPUT, UNTRUSTED_INPUT, screen_identifier, screen_text
from borges.armor.notes_guard import sanitize_notes
from borges.armor.report import QUARANTINE_TOKEN, ArmorReport

CORPUS = Path(__file__).parent / "corpus"
NAME_FIELDS = {"file_name", "column_name"}


def load(name: str) -> list[dict[str, Any]]:
    return json.loads((CORPUS / name).read_text(encoding="utf-8"))


def flagged(entry: dict[str, Any]) -> bool:
    field = entry["field"]
    if field == "column_notes":
        cleaned = sanitize_notes(entry["texts"], ArmorReport())
        return any(value == QUARANTINE_TOKEN for value in cleaned.values())
    text = entry["text"]
    if field in NAME_FIELDS:
        return bool(screen_identifier(text))
    profile = MODEL_OUTPUT if field == "model_output" else UNTRUSTED_INPUT
    return bool(screen_text(text, profile))


@dataclass(frozen=True)
class Score:
    true_positives: int
    false_negatives: list[str]
    false_positives: list[str]
    benign_total: int

    @property
    def recall(self) -> float:
        total = self.true_positives + len(self.false_negatives)
        return self.true_positives / total if total else 1.0

    @property
    def precision(self) -> float:
        flagged_total = self.true_positives + len(self.false_positives)
        return self.true_positives / flagged_total if flagged_total else 1.0


def evaluate() -> Score:
    attacks, benign = load("attacks.json"), load("benign.json")
    missed = [a["id"] for a in attacks if not flagged(a)]
    false_alarms = [b["id"] for b in benign if flagged(b)]
    return Score(len(attacks) - len(missed), missed, false_alarms, len(benign))
