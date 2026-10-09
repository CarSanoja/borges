from __future__ import annotations

from borges.analysis.models import ColumnProfile, DatasetProfile
from borges.armor.pii import TOKEN, find_pii
from borges.armor.pii_names import (
    PERSON_NAME_KIND,
    is_name_header,
    is_role_name_header,
    values_look_like_names,
)

NAME_TOKEN = TOKEN.format(kind=PERSON_NAME_KIND)
FREE_TEXT_WORDS = 5
FREE_TEXT_LENGTH = 40


def split_top_value(text: str) -> tuple[str, str]:
    head, sep, count = text.rpartition(": ")
    if sep and count.isdigit():
        return head, f": {count}"
    return text, ""


def column_values(profile: DatasetProfile, column: ColumnProfile) -> list[str]:
    values = [
        row[column.name] for row in profile.sample_rows if isinstance(row.get(column.name), str)
    ]
    tops = [
        split_top_value(v)[0]
        for k, v in column.summary.items()
        if k.startswith("top_") and isinstance(v, str)
    ]
    return [str(v) for v in values] + tops


def is_name_column(profile: DatasetProfile, column: ColumnProfile) -> bool:
    if column.dtype.startswith(("int", "uint", "float", "bool", "datetime")):
        return False
    if is_name_header(column.name):
        return True
    values = column_values(profile, column)
    role = is_role_name_header(column.name)
    return values_look_like_names(values, column.n_unique, profile.n_rows, role)


def person_name_columns(profile: DatasetProfile) -> set[str]:
    return {c.name for c in profile.columns if is_name_column(profile, c)}


def _has_pii(profile: DatasetProfile, column: ColumnProfile) -> bool:
    return any(find_pii(v, column.name) for v in column_values(profile, column))


def _free_text(profile: DatasetProfile, column: ColumnProfile) -> bool:
    values = column_values(profile, column)
    if not values:
        return False
    words = sum(len(v.split()) for v in values) / len(values)
    length = sum(len(v) for v in values) / len(values)
    return words >= FREE_TEXT_WORDS or length >= FREE_TEXT_LENGTH


def unsafe_key_columns(profile: DatasetProfile) -> set[str]:
    names = person_name_columns(profile)
    return names | {
        c.name for c in profile.columns if _has_pii(profile, c) or _free_text(profile, c)
    }
