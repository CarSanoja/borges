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
from borges.identity.principal import ANONYMOUS, Principal
from borges.identity.rate_limit import RateLimiter, RateState
from borges.identity.request_info import (
    client_of,
    forbidden_message,
    headers_of,
    is_public,
    permits,
)
from borges.identity.route_table import OPEN, RouteRequirement, match_route, scope_label
from borges.telemetry.policy_audit import audit_global

API_PREFIX = "/api"
CATCH_ALL = "/{path:path}"
DENY_AUDIT_INTERVAL_S = 10.0
SAFE_METHODS = ("GET", "HEAD")


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
            decision == "allow" and not always and method in SAFE_METHODS and is_public(requirement)
        )
        if quiet and not self.settings.borges_audit_reads:
            return
        data = {
            "method": method,
            "route": route or scope["path"][:120],
            "scope": scope_label(requirement) if requirement else None,
            "key_id": principal.key_id,
            "client": client_of(scope),
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
        authentication = self.authenticator.authenticate(headers_of(scope))
        principal = authentication.principal
        matched = match_route(scope["method"], path)
        route = matched[0] if matched else None
        requirement = matched[1] if matched else None
        if authentication.failure is not None:
            await self._bad_credentials(send, scope, route, requirement, authentication.failure)
            return
        if requirement is None and not self._serves(scope):
            await self.app(scope, receive, send)
            return
        if requirement is None:
            reason = "route declares no required scope; failing closed"
            await self._audit_deny(principal, reason, scope, route, None)
            await self._reject(send, 403, "This route is not declared in the access table.")
            return
        state = self.limiter.take(principal, client_of(scope))
        if not state.allowed:
            await self._rate_limited(send, principal, scope, route, requirement, state)
            return
        if requirement != OPEN and not permits(principal, requirement):
            reason = f"principal lacks {scope_label(requirement)}"
            await self._audit_deny(principal, reason, scope, route, requirement)
            await self._reject(send, 403, forbidden_message(principal, requirement))
            return
        scope.setdefault("state", {})["principal"] = principal
        await self._audit(principal, "allow", None, scope, route, requirement, False)
        await self.app(scope, receive, send)

    async def _audit_deny(
        self,
        principal: Principal,
        reason: str,
        scope: Scope,
        route: str | None,
        requirement: RouteRequirement | None,
    ) -> None:
        key = f"deny|{principal.id}|{client_of(scope)}|{scope['method']}|{route}|{reason[:60]}"
        if self._worth_auditing_deny(key):
            await self._audit(principal, "deny", reason, scope, route, requirement, True)

    async def _bad_credentials(
        self,
        send: Send,
        scope: Scope,
        route: str | None,
        requirement: RouteRequirement | None,
        failure: str,
    ) -> None:
        client = client_of(scope)
        state = self.limiter.take(ANONYMOUS, client)
        if not state.allowed:
            await self._rate_limited(
                send, ANONYMOUS, scope, route or scope["path"][:120], requirement, state
            )
            return
        reason = f"api key rejected: {failure}"
        await self._audit_deny(ANONYMOUS, reason, scope, route, requirement)
        if failure == "store_broken":
            await self._reject(
                send,
                503,
                "The key store failed integrity verification; keyed access is suspended. "
                "Anonymous public routes keep working.",
            )
            return
        await self._reject(send, 401, "The API key is not valid (unknown, revoked or expired).")

    async def _rate_limited(
        self,
        send: Send,
        principal: Principal,
        scope: Scope,
        route: str,
        requirement: RouteRequirement,
        state: RateState,
    ) -> None:
        key = self.limiter.bucket_key(principal, client_of(scope))
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
