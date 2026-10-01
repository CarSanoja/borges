from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx
import openai
from pydantic import BaseModel


class Answer(BaseModel):
    value: int
    label: str = "x"


def completion(
    text: str, tokens_in: int = 100, tokens_out: int = 20, finish_reason: str = "stop"
) -> SimpleNamespace:
    message = SimpleNamespace(content=text, reasoning_content="ignored")
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason=finish_reason)],
        usage=SimpleNamespace(prompt_tokens=tokens_in, completion_tokens=tokens_out),
    )


def bad_request() -> openai.BadRequestError:
    request = httpx.Request("POST", "https://example.test/v1/chat/completions")
    return openai.BadRequestError(
        "response_format unsupported", response=httpx.Response(400, request=request), body=None
    )


class FakeClient:
    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
