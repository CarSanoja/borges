from __future__ import annotations

from typing import Any

from borges.analysis.models import ColumnProfile, DatasetProfile
from borges.armor.errors import ArmorRefusal
from borges.armor.injection import screen_identifier
from borges.armor.notes_guard import sanitize_notes
from borges.armor.pii import find_pii, redact_pii
from borges.armor.pii_names import PERSON_NAME_KIND
from borges.armor.profile_pii import NAME_TOKEN, person_name_columns, split_top_value
from borges.armor.report import ArmorDecision, ArmorReport
from borges.armor.text_guard import injection_decision, pii_decisions, sanitize_value

DATASET_FALLBACK = "dataset"


def _name_cell(field: str, value: str, report: ArmorReport) -> str:
    if not value.strip() or "[redacted:" in value or "[quarantined" in value:
        return value
    report.add(ArmorDecision("redact", "pii", field, PERSON_NAME_KIND, 1))
    return NAME_TOKEN


def _cell(
    field: str, column: str, value: Any, report: ArmorReport, names: frozenset[str] = frozenset()
) -> Any:
    if isinstance(value, str):
        cleaned = sanitize_value(field, value, report, column)
        return _name_cell(field, cleaned, report) if column in names else cleaned
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) >= 10**12:
        text = str(value)
        if find_pii(text):
            for decision in pii_decisions(field, text):
                report.add(decision)
            return redact_pii(text)
    return value


def _top_value(field: str, value: str, report: ArmorReport) -> str:
    head, count = split_top_value(value)
    return _name_cell(field, head, report) + count


def _summary(
    column: ColumnProfile, report: ArmorReport, names: frozenset[str]
) -> dict[str, float | str]:
    cleaned: dict[str, float | str] = {}
    field = f"profile_value:{column.name}"
    for key, value in column.summary.items():
        if not isinstance(value, str):
            cleaned[key] = value
            continue
        text = sanitize_value(field, value, report, column.name)
        cleaned[key] = _top_value(field, text, report) if column.name in names else text
    return cleaned


def _guard_column(
    column: ColumnProfile, note: str | None, report: ArmorReport, names: frozenset[str]
) -> ColumnProfile:
    return column.model_copy(update={"summary": _summary(column, report, names), "note": note})


def _guard_rows(
    rows: list[dict[str, object]], report: ArmorReport, names: frozenset[str]
) -> list[dict[str, object]]:
    return [
        {key: _cell(f"sample_value:{key}", key, value, report, names) for key, value in row.items()}
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
    names = frozenset(person_name_columns(profile))
    columns = [_guard_column(c, notes.get(c.name), report, names) for c in profile.columns]
    rows = _guard_rows(profile.sample_rows, report, names)
    guarded = profile.model_copy(update={"name": name, "columns": columns, "sample_rows": rows})
    return guarded, report
