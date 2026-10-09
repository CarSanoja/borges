"""The names an uploaded table's columns get, and the column notes written against its headers.

A Spanish table with the headers "Horas de revisión", "Año" and "¿Reexpresó?" was stored with the
columns horas_de_revisi_n, a_o and _reexpres_: every accented letter became an underscore. A
letter with an accent keeps its base letter, ñ becomes ni, and underscores at the ends are dropped.

Column notes are matched to columns by name. A note written against the header the user typed
named no column after the rename, so it never reached the agents and nothing said so. A note whose
key is not a column is matched by the name that key gets, and a note that still matches nothing is
reported.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping

from borges.analysis.code_guard_rules import FORBIDDEN_MODULES, FORBIDDEN_NAMES


def safe_identifier(raw: object) -> str:
    text = str(raw).replace("ñ", "ni").replace("Ñ", "Ni")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"_{2,}", "_", re.sub(r"[^a-z0-9_]", "_", text.lower())).strip("_")
    if not text:
        return "column"
    if text[0].isdigit():
        text = f"_{text}"
    if text in FORBIDDEN_NAMES or text in FORBIDDEN_MODULES:
        text = f"{text}_col"
    return text


def match_notes(
    notes: Mapping[str, str], columns: Iterable[object]
) -> tuple[dict[str, str], list[str]]:
    names = {str(c) for c in columns}
    matched: dict[str, str] = {}
    unmatched: list[str] = []
    for key, note in notes.items():
        name = key if key in names else safe_identifier(key)
        if name in names:
            matched[name] = note
        else:
            unmatched.append(key)
    return matched, unmatched


def unmatched_caveat(unmatched: list[str]) -> str | None:
    if not unmatched:
        return None
    named = ", ".join(repr(k) for k in unmatched[:5])
    return (
        f"The column notes for {named} name no column of the table, so no agent saw them; "
        "notes are matched to the column names the upload shows."
    )
