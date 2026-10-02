from __future__ import annotations

from collections.abc import Mapping

from borges.armor.injection import screen_text
from borges.armor.report import QUARANTINE_TOKEN, ArmorReport
from borges.armor.text_guard import injection_decision, sanitize_value

MAX_NOTE_CHARS = 500


def sanitize_notes(notes: Mapping[str, str], report: ArmorReport) -> dict[str, str]:
    """Column notes are untrusted: quarantine hits, also when an attack is split across notes."""
    cleaned: dict[str, str] = {}
    for name, note in notes.items():
        cleaned[name] = sanitize_value(f"column_note:{name}", str(note)[:MAX_NOTE_CHARS], report)
    if QUARANTINE_TOKEN in cleaned.values() or not cleaned:
        return cleaned
    joined = screen_text("\n".join(cleaned.values()))
    if joined:
        report.add(injection_decision("column_notes:combined", "quarantine", joined))
        return {name: QUARANTINE_TOKEN for name in cleaned}
    return cleaned
