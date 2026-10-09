from __future__ import annotations

import pytest

from borges.armor.pii_names import is_name_header, is_name_value, values_look_like_names


@pytest.mark.parametrize(
    "header",
    ["Full Name", "first_name", "LAST-NAME", "surname", "employee_name"]
    + ["Apellidos", "nombre_completo", "customerName"],
)
def test_name_headers_are_recognised_by_any_case_and_separator(header: str) -> None:
    assert is_name_header(header)


@pytest.mark.parametrize(
    "header", ["department", "city", "filename", "salary", "name", "contact", "nombre", "", None]
)
def test_other_headers_are_not_names(header: str | None) -> None:
    assert not is_name_header(header)


@pytest.mark.parametrize(
    "value", ["Maria Lopez", "Juan de la Cruz", "Anne-Marie O'Neil", "John Q. Public Smith"]
)
def test_capitalised_alphabetic_words_are_names(value: str) -> None:
    assert is_name_value(value)


@pytest.mark.parametrize(
    "value", ["Sales", "new york city", "Room 12", "Maria", "A B C D E", "Alpha Beta 7"]
)
def test_other_strings_are_not_names(value: str) -> None:
    assert not is_name_value(value)


def test_unique_name_like_values_are_names_but_repeated_ones_are_not() -> None:
    sample = ["Maria Lopez", "John Smith", "Ana Ruiz", "Li Wei"]
    assert values_look_like_names(sample, n_unique=1500, n_rows=1500)
    assert not values_look_like_names(["New York", "Los Angeles", "San Diego"], 3, 1500)
    assert not values_look_like_names(sample[:2], n_unique=1500, n_rows=1500)
