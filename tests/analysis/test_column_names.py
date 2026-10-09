from __future__ import annotations

from borges.analysis.column_names import match_notes, safe_identifier, unmatched_caveat


def test_spanish_headers_keep_their_letters() -> None:
    headers = ["Horas de revisión", "Año", "¿Reexpresó?", "Sucursal Nº", "Ingreso (€)"]
    names = [safe_identifier(h) for h in headers]
    assert names == ["horas_de_revision", "anio", "reexpreso", "sucursal_no", "ingreso"]


def test_names_that_were_safe_do_not_change() -> None:
    assert [safe_identifier(h) for h in ("x", "client_id", "2024", "os")] == [
        "x",
        "client_id",
        "_2024",
        "os_col",
    ]


def test_a_note_written_against_the_header_reaches_its_column() -> None:
    notes = {"Horas de revisión": "blank when not logged", "saldo": "euros", "Ghost": "?"}
    matched, unmatched = match_notes(notes, ["horas_de_revision", "saldo"])
    assert matched == {"horas_de_revision": "blank when not logged", "saldo": "euros"}
    assert unmatched == ["Ghost"]
    caveat = unmatched_caveat(unmatched)
    assert caveat is not None and "'Ghost' name no column of the table" in caveat
    assert unmatched_caveat([]) is None
