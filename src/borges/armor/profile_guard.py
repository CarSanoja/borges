from __future__ import annotations

from typing import Any

from borges.analysis.models import ColumnProfile, DatasetProfile
from borges.armor.errors import ArmorRefusal
from borges.armor.injection import screen_identifier
from borges.armor.notes_guard import sanitize_notes
from borges.armor.pii import find_pii, redact_pii
from borges.armor.report import ArmorReport
from borges.armor.text_guard import injection_decision, pii_decisions, sanitize_value

DATASET_FALLBACK = "dataset"


def _cell(field: str, column: str, value: Any, report: ArmorReport) -> Any:
    if isinstance(value, str):
        return sanitize_value(field, value, report, column)
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) >= 10**12:
        text = str(value)
        if find_pii(text):
            for decision in pii_decisions(field, text):
                report.add(decision)
            return redact_pii(text)
    return value


def _summary(column: ColumnProfile, report: ArmorReport) -> dict[str, float | str]:
    cleaned: dict[str, float | str] = {}
    for key, value in column.summary.items():
        field = f"profile_value:{column.name}"
        cleaned[key] = (
            sanitize_value(field, value, report, column.name) if isinstance(value, str) else value
        )
    return cleaned


def _guard_column(column: ColumnProfile, note: str | None, report: ArmorReport) -> ColumnProfile:
    return column.model_copy(update={"summary": _summary(column, report), "note": note})


def _guard_rows(rows: list[dict[str, object]], report: ArmorReport) -> list[dict[str, object]]:
    return [
        {key: _cell(f"sample_value:{key}", key, value, report) for key, value in row.items()}
        for row in rows
    ]


def guard_profile(profile: DatasetProfile) -> tuple[DatasetProfile, ArmorReport]:
    """Everything a model will read about the data: names and notes quarantined, values redacted."""
    report = ArmorReport()
    refused = []
    for column in profile.columns:
        findings = screen_identifier(column.name)
        if findings:
            field = f"column_name:{column.name[:40]}"
            refused.append(injection_decision(field, "refuse", findings))
    if refused:
        raise ArmorRefusal(refused)
    name = profile.name
    if screen_identifier(name):
        name = DATASET_FALLBACK
    notes = sanitize_notes({c.name: c.note for c in profile.columns if c.note}, report)
    columns = [_guard_column(c, notes.get(c.name), report) for c in profile.columns]
    rows = _guard_rows(profile.sample_rows, report)
    guarded = profile.model_copy(update={"name": name, "columns": columns, "sample_rows": rows})
    return guarded, report
