from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_JSON_BYTES = 256 * 1024
UPLOAD_PATH = "/api/uploads"
BODY_METHODS = ("POST", "PUT", "PATCH")


class BodyTooLarge(BaseException):
    pass


class BodyLimitMiddleware:
    """Refuses oversized JSON request bodies before they are parsed; uploads have their own cap."""

    def __init__(self, app: ASGIApp, limit: int = MAX_JSON_BYTES) -> None:
        self.app = app
        self.limit = limit

    def _declared_too_large(self, scope: Scope) -> bool:
        for name, value in scope["headers"]:
            if name == b"content-length":
                try:
                    return int(value) > self.limit
                except ValueError:
                    return True
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        guarded = (
            scope["type"] == "http"
            and scope["method"] in BODY_METHODS
            and scope["path"].startswith("/api/")
            and scope["path"] != UPLOAD_PATH
        )
        if not guarded:
            await self.app(scope, receive, send)
            return
        if self._declared_too_large(scope):
            await self._reject(send)
            return
        seen = 0
        started = False

        async def counting() -> Message:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.limit:
                    raise BodyTooLarge
            return message

        async def tracking(message: Message) -> None:
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.app(scope, counting, tracking)
        except BodyTooLarge:
            if not started:
                await self._reject(send)

    async def _reject(self, send: Send) -> None:
        body = json.dumps({"detail": f"Request body exceeds {self.limit} bytes."}).encode()
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ]
        await send({"type": "http.response.start", "status": 413, "headers": headers})
        await send({"type": "http.response.body", "body": body})
