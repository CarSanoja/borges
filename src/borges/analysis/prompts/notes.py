from __future__ import annotations

from borges.analysis.models import DatasetProfile


def column_notes(profile: DatasetProfile) -> dict[str, str]:
    return {c.name: c.note for c in profile.columns if c.note}


def describe_column_notes(profile: DatasetProfile) -> str:
    notes = column_notes(profile)
    if not notes:
        return ""
    lines = "\n".join(f"- {name}: {note}" for name, note in notes.items())
    return (
        "Column notes (what each column means; read them before choosing or reading a "
        f"column):\n{lines}"
    )
