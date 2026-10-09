from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from borges.armor import pii_validators as check

EMAIL = re.compile(r"(?<![\w.%+-])[\w.%+-]+@[\w-]+(?:\.[\w-]+)*\.[^\W\d_]{2,}")
EMAIL_SPELLED = re.compile(
    r"(?<![\w.%+-])[\w.%+-]+\s?[\[(\{]\s?(?:at|@)\s?[\])\}]\s?[\w-]+(?:\.[\w-]+)*\.[^\W\d_]{2,}",
    re.IGNORECASE,
)
IBAN = re.compile(
    r"(?<![A-Za-z0-9])[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]{4}){2,7}(?:[ -]?[A-Z0-9]{1,3})?(?![A-Za-z0-9])",
    re.IGNORECASE,
)
CARD = re.compile(r"(?<![\w.-])\d(?:[ -]?\d){12,18}(?![\w-]|\.\d)")
SSN = re.compile(r"(?<![\w.-])\d{3}-\d{2}-\d{4}(?![\w-]|\.\d)")
CURP = re.compile(
    r"(?<![A-Za-z0-9])[A-Z]{4}\d{6}[HMX][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d(?![A-Za-z0-9])"
)
RFC = re.compile(r"(?<![A-Za-z0-9])[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}(?![A-Za-z0-9])")
DNI = re.compile(
    r"(?<![A-Za-z0-9])(?:\d{8}[- ]?[A-HJ-NP-TV-Z]|[XYZ][- ]?\d{7}[- ]?[A-HJ-NP-TV-Z])(?![A-Za-z0-9])",
    re.IGNORECASE,
)
PHONE = re.compile(
    r"(?<![\w.+-])(?:\+\d{1,3}[ .-]?)?(?:\(\d{2,4}\)[ .-]?)?\d{2,4}[ .-]\d{2,4}[ .-]\d{2,4}(?:[ .-]\d{2,4})?(?![\w-])"
    r"|(?<![\w.+-])(?:\+\d{1,3}[ .-]?)?\(\d{2,4}\)[ .-]?\d{2,4}[ .-]\d{2,4}(?![\w-])"
    r"|(?<![\w.])\+\d{9,15}(?![\w])"
)
MEDICAL_RECORD = re.compile(r"(?<![A-Za-z0-9])(?:MRN|NHC)[-:# ]?\d{5,12}(?!\d)", re.IGNORECASE)
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w]|\.\d)")
IPV6 = re.compile(
    r"(?<![\w:])(?:(?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}"
    r"|(?:[0-9A-Fa-f]{1,4}:){1,6}:(?:[0-9A-Fa-f]{1,4}(?::[0-9A-Fa-f]{1,4}){0,5})?)(?![\w:])"
)
DOB_VALUE = re.compile(
    r"(?<!\d)(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})(?:[T ]\d{2}:\d{2}(?::\d{2})?)?(?!\d)"
)
DOB_COLUMN = re.compile(r"(?i)(birth|dob|born|nacimiento|nacim|cumple|birthday|fecha_nac)")
ISO_DATE_START = re.compile(r"^\d{4}-\d{2}-\d{2}")
SSN_SHAPE = re.compile(r"\d{3}-\d{2}-\d{4}")

Validator = Callable[[str], bool]


@dataclass(frozen=True)
class Detector:
    kind: str
    pattern: re.Pattern[str]
    validate: Validator | None = None


def phone_valid(raw: str) -> bool:
    digits = re.sub(r"\D", "", raw)
    if ISO_DATE_START.match(raw.strip()) or SSN_SHAPE.fullmatch(raw.strip()):
        return False
    return 9 <= len(digits) <= 15


DETECTORS: tuple[Detector, ...] = (
    Detector("email", EMAIL),
    Detector("email", EMAIL_SPELLED),
    Detector("iban", IBAN, check.iban_valid),
    Detector("card", CARD, check.card_valid),
    Detector("ssn", SSN),
    Detector("curp", CURP, check.curp_valid),
    Detector("rfc", RFC, check.rfc_valid),
    Detector("dni_nie", DNI, check.dni_valid),
    Detector("medical_record", MEDICAL_RECORD),
    Detector("phone", PHONE, phone_valid),
    Detector("ip_address", IPV4, check.ipv4_valid),
    Detector("ip_address", IPV6),
)

KINDS = (
    "email",
    "phone",
    "card",
    "iban",
    "ssn",
    "dni_nie",
    "curp",
    "rfc",
    "ip_address",
    "medical_record",
    "date_of_birth",
    "person_name",
)
