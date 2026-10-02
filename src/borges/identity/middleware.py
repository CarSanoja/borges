from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable, Iterable
from typing import Any

from starlette.routing import Match
from starlette.types import ASGIApp, Receive, Scope, Send

from borges.config import Settings
from borges.identity.authentication import Authenticator
from borges.identity.principal import Principal
from borges.identity.rate_limit import RateLimiter, RateState
from borges.identity.route_table import OPEN, RouteRequirement, match_route, scope_label
from borges.identity.scopes import PUBLIC_SCOPES
from borges.telemetry.policy_audit import audit_global

API_PREFIX = "/api"
CATCH_ALL = "/{path:path}"
DENY_AUDIT_INTERVAL_S = 10.0
SAFE_METHODS = ("GET", "HEAD")


def _client(scope: Scope) -> str:
    client = scope.get("client")
    return str(client[0]) if client else "unknown"


def _headers(scope: Scope) -> dict[str, str]:
    return {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}


class IdentityMiddleware:
    """Resolves the principal, rate-limits it and enforces the route table, failing closed."""

    def __init__(
        self,
        app: ASGIApp,
        settings: Settings,
        routes_of: Callable[[], Iterable[Any]],
        authenticator: Authenticator | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        self.app = app
        self.settings = settings
        self.routes_of = routes_of
        self.authenticator = authenticator or Authenticator(settings)
        self.limiter = limiter or RateLimiter(settings)
        self._last_deny_audit: dict[str, float] = {}

    async def _audit(
        self,
        principal: Principal,
        decision: str,
        reason: str | None,
        scope: Scope,
        route: str | None,
        requirement: RouteRequirement | None,
        always: bool,
    ) -> None:
        method = scope["method"]
        quiet = (
            decision == "allow" and not always and method in SAFE_METHODS and _public(requirement)
        )
        if quiet and not self.settings.borges_audit_reads:
            return
        data = {
            "method": method,
            "route": route or scope["path"][:120],
            "scope": scope_label(requirement) if requirement else None,
            "key_id": principal.key_id,
            "client": _client(scope),
        }
        await asyncio.to_thread(
            audit_global,
            self.settings,
            "identity.access",
            principal=principal.id,
            decision=decision,
            reason=reason,
            data=data,
        )

    def _serves(self, scope: Scope) -> bool:
        for route in self.routes_of():
            if getattr(route, "path", None) == CATCH_ALL:
                continue
            match, _ = route.matches(scope)
            if match != Match.NONE:
                return True
        return False

    def _worth_auditing_deny(self, key: str) -> bool:
        now = time.monotonic()
        if now - self._last_deny_audit.get(key, -DENY_AUDIT_INTERVAL_S) < DENY_AUDIT_INTERVAL_S:
            return False
        self._last_deny_audit[key] = now
        if len(self._last_deny_audit) > 5000:
            self._last_deny_audit.clear()
        return True

    @staticmethod
    async def _reject(
        send: Send, status: int, detail: str, headers: list[tuple[bytes, bytes]] | None = None
    ) -> None:
        body = json.dumps({"detail": detail}).encode("utf-8")
        head = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ]
        await send(
            {"type": "http.response.start", "status": status, "headers": head + (headers or [])}
        )
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or not (path == API_PREFIX or path.startswith(API_PREFIX + "/")):
            await self.app(scope, receive, send)
            return
        if scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return
        authentication = self.authenticator.authenticate(_headers(scope))
        principal = authentication.principal
        matched = match_route(scope["method"], path)
        route = matched[0] if matched else None
        requirement = matched[1] if matched else None
        if authentication.failure is not None:
            reason = f"api key rejected: {authentication.failure}"
            await self._audit(principal, "deny", reason, scope, route, requirement, True)
            await self._reject(send, 401, "The API key is not valid (unknown, revoked or expired).")
            return
        if requirement is None and not self._serves(scope):
            await self.app(scope, receive, send)
            return
        if requirement is None:
            reason = "route declares no required scope; failing closed"
            await self._audit(principal, "deny", reason, scope, route, None, True)
            await self._reject(send, 403, "This route is not declared in the access table.")
            return
        state = self.limiter.take(principal, _client(scope))
        if not state.allowed:
            await self._rate_limited(send, principal, scope, route, requirement, state)
            return
        if requirement != OPEN and not _permits(principal, requirement):
            reason = f"principal lacks {scope_label(requirement)}"
            await self._audit(principal, "deny", reason, scope, route, requirement, True)
            await self._reject(send, 403, _forbidden(principal, requirement))
            return
        scope.setdefault("state", {})["principal"] = principal
        await self._audit(principal, "allow", None, scope, route, requirement, False)
        await self.app(scope, receive, send)

    async def _rate_limited(
        self,
        send: Send,
        principal: Principal,
        scope: Scope,
        route: str,
        requirement: RouteRequirement,
        state: RateState,
    ) -> None:
        key = self.limiter.bucket_key(principal, _client(scope))
        if self._worth_auditing_deny(key):
            await self._audit(
                principal, "deny", "rate limit exceeded", scope, route, requirement, True
            )
        retry = max(1, int(state.retry_after_s + 0.999))
        await self._reject(
            send,
            429,
            f"Rate limit exceeded for {principal.id}; retry in {retry}s.",
            [(b"retry-after", str(retry).encode())],
        )


def _public(requirement: RouteRequirement | None) -> bool:
    if requirement is None or requirement == OPEN:
        return True
    scopes = {requirement} if isinstance(requirement, str) else set(requirement)
    return scopes <= PUBLIC_SCOPES


def _permits(principal: Principal, requirement: RouteRequirement) -> bool:
    if isinstance(requirement, str):
        return principal.has(requirement)
    return principal.has_any(requirement)


def _forbidden(principal: Principal, requirement: RouteRequirement) -> str:
    who = "Anonymous demo access" if principal.anonymous else principal.id
    hint = " Paste an API key with this scope in the header." if principal.anonymous else ""
    return f"{who} lacks the required scope: {scope_label(requirement)}.{hint}"
