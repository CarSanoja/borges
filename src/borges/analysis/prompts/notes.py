from __future__ import annotations

import re

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


def describe_named_columns(profile: DatasetProfile, text: str) -> str:
    """An audit run's judge rejected partner-clustered errors because "the column notes do not
    confirm at least 30 distinct partners" (r_20261009T065046_56b2c6): the data had 40, and the
    judge saw only the notes. It now sees how many distinct values each column the option names
    holds."""
    named = [
        c
        for c in profile.columns
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(c.name)}(?![A-Za-z0-9_])", text)
    ]
    if not named:
        return ""
    lines = "\n".join(f"- {c.name}: {c.n_unique:,} distinct values" for c in named[:12])
    return f"Columns this option names, in {profile.n_rows:,} rows:\n{lines}"
