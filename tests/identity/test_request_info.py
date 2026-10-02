from __future__ import annotations

from borges.identity.request_info import DUPLICATE_AUTHORIZATION, client_of, headers_of


def scope(headers: list[tuple[bytes, bytes]], client=("1.2.3.4", 5)) -> dict:
    return {"headers": headers, "client": client}


def test_headers_are_lowercased() -> None:
    assert headers_of(scope([(b"X-Thing", b"a")])) == {"x-thing": "a"}


def test_a_second_authorization_header_poisons_the_value() -> None:
    parsed = headers_of(scope([(b"Authorization", b"Bearer a"), (b"authorization", b"Bearer b")]))
    assert parsed["authorization"] == DUPLICATE_AUTHORIZATION


def test_client_falls_back_to_unknown() -> None:
    assert client_of(scope([])) == "1.2.3.4"
    assert client_of(scope([], client=None)) == "unknown"
