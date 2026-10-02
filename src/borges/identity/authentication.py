from __future__ import annotations

import hmac
from collections.abc import Mapping
from dataclasses import dataclass

from borges.config import Settings
from borges.identity.keystore import AuthFailure, KeyStore, open_keystore
from borges.identity.principal import ANONYMOUS, LEGACY, Principal

AUTHORIZATION = "authorization"
LEGACY_HEADER = "x-borges-live-token"
BEARER = "bearer "


@dataclass(frozen=True)
class Authentication:
    principal: Principal
    failure: AuthFailure | None = None


def _bearer(headers: Mapping[str, str]) -> str | None:
    value = headers.get(AUTHORIZATION)
    if value is None:
        return None
    if value[: len(BEARER)].lower() == BEARER:
        return value[len(BEARER) :].strip()
    return ""


def _legacy_matches(settings: Settings, headers: Mapping[str, str]) -> bool:
    expected = settings.borges_live_token
    supplied = headers.get(LEGACY_HEADER)
    if not expected or supplied is None:
        return False
    return hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))


class Authenticator:
    def __init__(self, settings: Settings, keystore: KeyStore | None = None) -> None:
        self.settings = settings
        self.keystore = keystore or open_keystore(settings)

    def authenticate(self, headers: Mapping[str, str]) -> Authentication:
        token = _bearer(headers)
        if token is not None:
            record, failure = self.keystore.authenticate(token)
            if record is None:
                return Authentication(ANONYMOUS, failure or "malformed")
            return Authentication(record.principal())
        if _legacy_matches(self.settings, headers):
            return Authentication(LEGACY)
        return Authentication(ANONYMOUS)
