from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

TokenFailure = Literal["malformed", "bad_signature", "expired", "wrong_run", "wrong_agent"]


class AgentTokenInvalid(PermissionError):
    def __init__(self, failure: TokenFailure, detail: str) -> None:
        super().__init__(f"agent token rejected ({failure}): {detail}")
        self.failure: TokenFailure = failure
        self.detail = detail


@dataclass(frozen=True)
class AgentClaims:
    run_id: str
    principal: str
    capabilities: frozenset[str]
    issued_at: float
    expires_at: float
    jti: str


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class AgentTokenIssuer:
    """Mints and verifies per-agent HMAC-SHA256 tokens; the secret stays in memory."""

    def __init__(self, secret: bytes | None = None, clock: Callable[[], float] = time.time) -> None:
        self._secret = secret or secrets.token_bytes(32)
        self._clock = clock

    def _sign(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode("ascii"), hashlib.sha256).hexdigest()

    def mint(self, run_id: str, principal: str, capabilities: Iterable[str], ttl_s: float) -> str:
        now = self._clock()
        body = {
            "run": run_id,
            "sub": principal,
            "cap": sorted(set(capabilities)),
            "iat": now,
            "exp": now + ttl_s,
            "jti": secrets.token_hex(8),
        }
        payload = _b64(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return f"{payload}.{self._sign(payload)}"

    def verify(
        self, token: str, run_id: str | None = None, principal: str | None = None
    ) -> AgentClaims:
        payload, _, signature = token.partition(".")
        if not payload or not signature or not token.isascii():
            raise AgentTokenInvalid("malformed", "not a payload.signature token")
        if not hmac.compare_digest(self._sign(payload), signature):
            raise AgentTokenInvalid("bad_signature", "signature does not match")
        try:
            body = json.loads(_unb64(payload))
            claims = AgentClaims(
                run_id=str(body["run"]),
                principal=str(body["sub"]),
                capabilities=frozenset(str(c) for c in body["cap"]),
                issued_at=float(body["iat"]),
                expires_at=float(body["exp"]),
                jti=str(body["jti"]),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise AgentTokenInvalid("malformed", "payload cannot be read") from exc
        if self._clock() >= claims.expires_at:
            raise AgentTokenInvalid("expired", f"expired at {claims.expires_at:.0f}")
        if run_id is not None and claims.run_id != run_id:
            raise AgentTokenInvalid("wrong_run", f"token belongs to run {claims.run_id}")
        if principal is not None and claims.principal != principal:
            raise AgentTokenInvalid("wrong_agent", f"token belongs to {claims.principal}")
        return claims


_PROCESS_ISSUER: AgentTokenIssuer | None = None


def process_issuer() -> AgentTokenIssuer:
    global _PROCESS_ISSUER
    if _PROCESS_ISSUER is None:
        _PROCESS_ISSUER = AgentTokenIssuer()
    return _PROCESS_ISSUER
