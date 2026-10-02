from __future__ import annotations

import re
from datetime import date

DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
CURP_ALPHABET = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
CARD_PREFIXES = (
    r"4",
    r"5[1-5]",
    r"2(?:2[2-9][1-9]|2[3-9]\d|[3-6]\d\d|7[01]\d|720)",
    r"3[47]",
    r"3(?:0[0-5]|[68])",
    r"35(?:2[89]|[3-8]\d)",
    r"6(?:011|5\d\d|4[4-9]\d)",
    r"62",
)
_CARD_PREFIX = re.compile("|".join(f"^(?:{p})" for p in CARD_PREFIXES))
IBAN_LENGTHS = {
    "AT": 20,
    "BE": 16,
    "CH": 21,
    "DE": 22,
    "DK": 18,
    "ES": 24,
    "FI": 18,
    "FR": 27,
    "GB": 22,
    "GR": 27,
    "IE": 22,
    "IT": 27,
    "LU": 20,
    "NL": 18,
    "NO": 15,
    "PL": 28,
    "PT": 25,
    "SE": 24,
    "TR": 26,
}


def luhn_valid(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def card_valid(raw: str) -> bool:
    digits = re.sub(r"[ -]", "", raw)
    if not digits.isdigit() or not 13 <= len(digits) <= 19:
        return False
    return bool(_CARD_PREFIX.match(digits)) and luhn_valid(digits)


def iban_valid(raw: str) -> bool:
    compact = re.sub(r"\s", "", raw).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", compact):
        return False
    expected = IBAN_LENGTHS.get(compact[:2])
    if expected is not None and len(compact) != expected:
        return False
    rearranged = compact[4:] + compact[:4]
    number = "".join(str(int(char, 36)) for char in rearranged)
    return int(number) % 97 == 1


def ssn_valid(raw: str) -> bool:
    area, group, serial = raw.split("-")
    if area in ("000", "666") or area.startswith("9"):
        return False
    return group != "00" and serial != "0000"


def dni_valid(raw: str) -> bool:
    compact = re.sub(r"[- ]", "", raw).upper()
    if compact[0] in "XYZ":
        number = int("XYZ".index(compact[0]).__str__() + compact[1:-1])
    else:
        number = int(compact[:-1])
    return DNI_LETTERS[number % 23] == compact[-1]


def _valid_yymmdd(chunk: str) -> bool:
    year, month, day = int(chunk[:2]), int(chunk[2:4]), int(chunk[4:6])
    for century in (1900, 2000):
        try:
            date(century + year, month, day)
            return True
        except ValueError:
            continue
    return False


def curp_valid(raw: str) -> bool:
    if not _valid_yymmdd(raw[4:10]):
        return False
    total = sum(CURP_ALPHABET.index(char) * (18 - index) for index, char in enumerate(raw[:17]))
    return str((10 - total % 10) % 10) == raw[17]


def rfc_valid(raw: str) -> bool:
    head = 4 if len(raw) == 13 else 3
    return _valid_yymmdd(raw[head : head + 6])


def ipv4_valid(raw: str) -> bool:
    parts = raw.split(".")
    return len(parts) == 4 and all(p.isdigit() and int(p) <= 255 for p in parts)
