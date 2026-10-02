from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from borges.llm.cache import atomic_write_text
from borges.llm.client import LLMError
from borges.llm.nebius_transport import estimate_prompt_tokens
from borges.llm.scripted_provider import fixture_name


def read_completion(
    response: Any, messages: list[dict[str, str]], max_tokens: int
) -> tuple[str, int, int, bool]:
    try:
        text = response.choices[0].message.content or ""
    except (AttributeError, IndexError) as exc:
        raise LLMError("model response has no message content") from exc
    truncated = getattr(response.choices[0], "finish_reason", None) == "length"
    usage = getattr(response, "usage", None)
    tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
    tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
    if usage is None or not (tokens_in or tokens_out):
        tokens_in, tokens_out = estimate_prompt_tokens(messages), max_tokens
    return text, tokens_in, tokens_out, truncated


def write_fixture(record_dir: Path, key: str, record: dict[str, Any]) -> None:
    atomic_write_text(record_dir / fixture_name(key), json.dumps(record, ensure_ascii=False))


async def with_reservation[T](
    guards: tuple[Any, ...], estimate: float, call: Callable[[], Awaitable[T]]
) -> T:
    reserved: list[Any] = []
    try:
        for guard in (g for g in guards if g is not None):
            await guard.reserve(estimate)
            reserved.append(guard)
        return await call()
    except BaseException:
        for guard in reserved:
            await guard.release(estimate)
        raise
