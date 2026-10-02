from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from borges.llm.client import LLMError, LLMResponse, Role, Usage, UsageTotals
from borges.llm.json_output import parse_model

SCRIPTED_MODEL = "scripted"
_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]|\.{2,}")


def fixture_name(key: str) -> str:
    return _UNSAFE.sub("_", key.replace(":", "__")) + ".json"


class ScriptedLLM:
    """Replays recorded responses from `fixtures_dir`, at zero cost."""

    def __init__(self, fixtures_dir: Path, latency_s: float = 0.0) -> None:
        self.fixtures_dir = fixtures_dir
        self.latency_s = latency_s
        self.totals = UsageTotals()

    def _load(self, key: str) -> dict[str, Any]:
        path = self.fixtures_dir / fixture_name(key)
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise LLMError(f"no scripted response for key {key!r} ({path})") from exc
        except json.JSONDecodeError as exc:
            raise LLMError(f"scripted response for key {key!r} is not valid JSON") from exc
        if not isinstance(record, dict):
            raise LLMError(f"scripted response for key {key!r} must be a JSON object")
        return record

    async def complete(
        self,
        role: Role,
        messages: list[dict[str, str]],
        *,
        key: str,
        schema: type[BaseModel] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> LLMResponse:
        started = time.perf_counter()
        record = self._load(key)
        text = str(record.get("text", ""))
        parsed = record.get("parsed")
        if schema is not None:
            if parsed is not None:
                try:
                    validated = schema.model_validate(parsed)
                except ValueError as exc:
                    raise LLMError(f"scripted response for key {key!r} is invalid: {exc}") from exc
            else:
                validated = parse_model(text, schema)
            parsed = validated.model_dump(mode="json")
        if self.latency_s > 0:
            await asyncio.sleep(self.latency_s)
        usage = Usage(
            model=SCRIPTED_MODEL,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
        )
        self.totals.add(usage)
        return LLMResponse(
            role=role,
            text=text,
            parsed=parsed,
            usage=usage,
            latency_s=time.perf_counter() - started,
        )
