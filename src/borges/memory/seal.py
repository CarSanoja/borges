from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PLAIN = b"P"
SEALED = b"E"
NONCE_BYTES = 12


class SealError(ValueError):
    pass


class Sealer:
    """AES-GCM under a per-tenant derived key, or plain rows when no key is set."""

    def __init__(self, key: str | None) -> None:
        self._key = key or None

    @property
    def encrypted(self) -> bool:
        return self._key is not None

    def _cipher(self, tenant: str) -> AESGCM:
        assert self._key is not None
        material = hmac.new(
            self._key.encode("utf-8"), f"borges-memory\0{tenant}".encode(), hashlib.sha256
        )
        return AESGCM(material.digest())

    def seal(self, tenant: str, aad: str, payload: dict[str, Any]) -> bytes:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if self._key is None:
            return PLAIN + raw
        nonce = os.urandom(NONCE_BYTES)
        return SEALED + nonce + self._cipher(tenant).encrypt(nonce, raw, aad.encode("utf-8"))

    def open(self, tenant: str, aad: str, blob: bytes, allow_plain: bool) -> dict[str, Any]:
        tag, body = blob[:1], blob[1:]
        if tag == PLAIN:
            if not allow_plain:
                raise SealError("a plain memory row is not accepted for this tenant")
            return _decode(body)
        if tag != SEALED:
            raise SealError("unknown memory row format")
        if self._key is None:
            raise SealError("the row is encrypted and BORGES_MEMORY_KEY is not set")
        try:
            raw = self._cipher(tenant).decrypt(
                body[:NONCE_BYTES], body[NONCE_BYTES:], aad.encode("utf-8")
            )
        except InvalidTag as exc:
            raise SealError("the row cannot be decrypted with this key and tenant") from exc
        return _decode(raw)


def _decode(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except ValueError as exc:
        raise SealError("the row is not valid JSON") from exc
    if not isinstance(value, dict):
        raise SealError("the row is not a JSON object")
    return value
