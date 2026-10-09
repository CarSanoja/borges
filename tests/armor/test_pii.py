from __future__ import annotations

import pytest

from borges.armor.pii import count_pii, find_pii, is_dob_column, redact_pii


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("write to jo.doe@example.com", "email"),
        ("call +34 612 345 678", "phone"),
        ("call (555) 123-4567", "phone"),
        ("card 4111 1111 1111 1111", "card"),
        ("iban ES91 2100 0418 4502 0005 1332", "iban"),
        ("ssn 123-45-6789", "ssn"),
        ("dni 12345678Z", "dni_nie"),
        ("nie X1234567L", "dni_nie"),
        ("curp HEGG560427MVZRRL04", "curp"),
        ("rfc HEGG560427ABC", "rfc"),
        ("host 192.168.1.10", "ip_address"),
        ("host 2001:0db8:85a3:0000:0000:8a2e:0370:7334", "ip_address"),
        ("chart MRN-4821937", "medical_record"),
        ("historia NHC 0012345", "medical_record"),
    ],
)
def test_each_kind_is_detected_and_redacted(text: str, kind: str) -> None:
    assert [m.kind for m in find_pii(text)] == [kind]
    assert f"[redacted:{kind}]" in redact_pii(text)


@pytest.mark.parametrize(
    "text",
    [
        "2024-01-15 10:30:45",
        "estimate 0.0123 with n = 10535",
        "4111 1111 1111 1112",
        "version 1.2.3",
        "u_4e00fbb461 r_20261002T101112_ab12cd",
        "12345678A",
        "1,234,567",
        '"ci_low":-1.5531274261561,"p":0.21645021645021753',
        "visit V100023",
    ],
)
def test_lookalikes_are_not_flagged(text: str) -> None:
    assert find_pii(text) == []


def test_date_of_birth_only_when_the_column_says_so() -> None:
    assert find_pii("1985-03-02") == []
    assert [m.kind for m in find_pii("1985-03-02", "date_of_birth")] == ["date_of_birth"]
    assert redact_pii("born 02/03/1985", "dob") == "born [redacted:date_of_birth]"
    assert is_dob_column("fecha_nacimiento") and not is_dob_column("order_date")


def test_count_and_overlap_resolution() -> None:
    counts = count_pii("a@b.co, c@d.org and +34 612 345 678")
    assert counts == {"email": 2, "phone": 1}
    assert redact_pii("ok") == "ok" and redact_pii("") == ""


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("es9121000418450200051332", "iban"),
        ("es91 2100 0418 4502 0005 1332", "iban"),
        ("ES91-2100-0418-4502-0005-1332", "iban"),
        ("josé@example.com", "email"),
        ("user@münchen.de", "email"),
        ("john.doe[at]example.com", "email"),
        ("12345678z", "dni_nie"),
        ("4111 1111 1111 1111", "card"),
        ("4111​1111​1111​1111", "card"),
        ("john​@example.com", "email"),
        ("ｊｏｈｎ@example.com", "email"),
    ],
)
def test_disguised_personal_data_is_found_and_redacted(text: str, kind: str) -> None:
    assert [m.kind for m in find_pii(text)] == [kind]
    assert redact_pii(text) == f"[redacted:{kind}]"


def test_personal_data_far_into_a_long_text_is_still_redacted() -> None:
    long = "x " * 30000 + "victim@example.com card 4111 1111 1111 1111"
    cleaned = redact_pii(long)
    assert "victim@example.com" not in cleaned and "4111" not in cleaned
    assert cleaned.endswith("[redacted:email] card [redacted:card]")


def test_text_beyond_the_scan_limit_is_cut_rather_than_leaked(monkeypatch) -> None:
    monkeypatch.setattr("borges.armor.pii.MAX_SCAN_CHARS", 50)
    cleaned = redact_pii("a" * 60 + " leak@example.com")
    assert "leak@example.com" not in cleaned and cleaned.endswith("[redacted:unscanned]")


def test_ssn_shaped_strings_are_redacted_even_with_an_invalid_serial() -> None:
    assert [m.kind for m in find_pii("123-45-0000")] == ["ssn"]
    assert redact_pii("id 000-12-3456 here") == "id [redacted:ssn] here"
