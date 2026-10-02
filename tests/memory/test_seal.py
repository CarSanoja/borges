from __future__ import annotations

import pytest

from borges.memory.seal import Sealer, SealError

PAYLOAD = {"text": "secret column meaning"}


def test_encrypted_blob_hides_the_payload_and_round_trips() -> None:
    sealer = Sealer("k" * 32)
    blob = sealer.seal("acme", "aad", PAYLOAD)
    assert b"secret" not in blob
    assert sealer.open("acme", "aad", blob, allow_plain=False) == PAYLOAD


def test_another_tenant_or_context_cannot_open_it() -> None:
    sealer = Sealer("k" * 32)
    blob = sealer.seal("acme", "aad", PAYLOAD)
    with pytest.raises(SealError):
        sealer.open("rival", "aad", blob, allow_plain=False)
    with pytest.raises(SealError):
        sealer.open("acme", "other", blob, allow_plain=False)
    with pytest.raises(SealError):
        Sealer("z" * 32).open("acme", "aad", blob, allow_plain=False)


def test_a_tampered_blob_is_refused() -> None:
    sealer = Sealer("k" * 32)
    blob = bytearray(sealer.seal("acme", "aad", PAYLOAD))
    blob[-1] ^= 1
    with pytest.raises(SealError):
        sealer.open("acme", "aad", bytes(blob), allow_plain=False)


def test_without_a_key_rows_are_plain_and_only_the_public_tenant_may_read_them() -> None:
    sealer = Sealer(None)
    assert sealer.encrypted is False
    blob = sealer.seal("public-demo", "aad", PAYLOAD)
    assert b"secret" in blob
    assert sealer.open("public-demo", "aad", blob, allow_plain=True) == PAYLOAD
    with pytest.raises(SealError):
        sealer.open("acme", "aad", blob, allow_plain=False)


def test_an_encrypted_row_cannot_be_read_without_the_key() -> None:
    blob = Sealer("k" * 32).seal("acme", "aad", PAYLOAD)
    with pytest.raises(SealError):
        Sealer(None).open("acme", "aad", blob, allow_plain=False)


def test_unknown_formats_are_refused() -> None:
    with pytest.raises(SealError):
        Sealer(None).open("t", "a", b"Xjunk", allow_plain=True)
    with pytest.raises(SealError):
        Sealer(None).open("t", "a", b"Pnot json", allow_plain=True)
    with pytest.raises(SealError):
        Sealer(None).open("t", "a", b"P[1]", allow_plain=True)
