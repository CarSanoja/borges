from __future__ import annotations

from typing import Any

from borges.armor.injection import MODEL_OUTPUT, screen_text
from borges.armor.option_guard import poison_decision
from borges.armor.report import QUARANTINE_TOKEN, ArmorReport
from borges.armor.text_guard import sanitize_value
from borges.memory.kinds import MemoryKind

TEXT_FIELDS: dict[MemoryKind, tuple[str, ...]] = {
    MemoryKind.VERDICT: ("reason", "source", "text"),
    MemoryKind.CODE: ("code",),
    MemoryKind.ADVERSARY: ("label", "spec", "reason", "why"),
}


def screen_payload(
    kind: MemoryKind, payload: dict[str, Any], report: ArmorReport, field: str
) -> dict[str, Any] | None:
    """Memories are untrusted input: None means the entry must not reach any prompt."""
    if kind is MemoryKind.NOTE:
        cleaned = sanitize_value(field, str(payload.get("text", "")), report)
        if cleaned == QUARANTINE_TOKEN:
            return None
        return {**payload, "text": cleaned}
    joined = "\n".join(str(payload.get(name) or "") for name in TEXT_FIELDS[kind])
    findings = screen_text(joined, MODEL_OUTPUT)
    if findings:
        report.add(poison_decision(field, "drop", findings))
        return None
    return payload
