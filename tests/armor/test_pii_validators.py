from __future__ import annotations

from borges.armor import pii_validators as v


def test_luhn_and_card_prefix() -> None:
    assert v.luhn_valid("4111111111111111")
    assert v.card_valid("4111 1111 1111 1111") and v.card_valid("378282246310005")
    assert not v.card_valid("4111 1111 1111 1112")
    assert not v.card_valid("1234567812345670")


def test_iban_checksum_and_length() -> None:
    assert v.iban_valid("ES91 2100 0418 4502 0005 1332")
    assert v.iban_valid("GB82WEST12345698765432")
    assert not v.iban_valid("ES91 2100 0418 4502 0005 1333")
    assert not v.iban_valid("ES9121000418450200051")


def test_ssn_rules() -> None:
    assert v.ssn_valid("123-45-6789")
    assert not v.ssn_valid("000-45-6789") and not v.ssn_valid("666-45-6789")
    assert not v.ssn_valid("900-45-6789") and not v.ssn_valid("123-00-6789")
    assert not v.ssn_valid("123-45-0000")


def test_dni_and_nie_letters() -> None:
    assert v.dni_valid("12345678Z") and v.dni_valid("12345678-Z")
    assert not v.dni_valid("12345678A")
    assert v.dni_valid("X1234567L") and not v.dni_valid("X1234567A")


def test_curp_and_rfc() -> None:
    assert v.curp_valid("HEGG560427MVZRRL04")
    assert not v.curp_valid("HEGG560427MVZRRL05")
    assert not v.curp_valid("HEGG561327MVZRRL04")
    assert v.rfc_valid("HEGG560427ABC") and v.rfc_valid("ABC560427XY1")
    assert not v.rfc_valid("HEGG561327ABC")


def test_ipv4_octets() -> None:
    assert v.ipv4_valid("192.168.1.10") and not v.ipv4_valid("300.1.1.1")
