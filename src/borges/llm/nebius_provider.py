from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import openai
from pydantic import BaseModel

from borges.llm.cache import DiskCache, atomic_write_text, cache_key
from borges.llm.client import (
    DEFAULT_ROLE_MODELS,
    LLMError,
    LLMResponse,
    ModelSpec,
    Role,
    Usage,
    UsageTotals,
)
from borges.llm.json_output import parse_model, schema_instructions
from borges.llm.scripted_provider import fixture_name
from borges.llm.spend import RunBudget, SpendLedger

CHARS_PER_TOKEN = 3.5


def with_schema_instructions(
    messages: list[dict[str, str]], schema: type[BaseModel]
) -> list[dict[str, str]]:
    instructions = schema_instructions(schema)
    if messages and messages[0]["role"] == "system":
        head = {"role": "system", "content": f"{messages[0]['content']}\n\n{instructions}"}
        return [head, *messages[1:]]
    return [{"role": "system", "content": instructions}, *messages]


class NebiusLLM:
    """Role-routed client for Nebius Token Factory, with cache, spend caps and recording."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        role_models: dict[Role, ModelSpec] = DEFAULT_ROLE_MODELS,
        cache: DiskCache | None = None,
        ledger: SpendLedger | None = None,
        run_budget: RunBudget | None = None,
        record_dir: Path | None = None,
        client: Any = None,
    ) -> None:
        self.role_models = role_models
        self.cache = cache
        self.ledger = ledger
        self.run_budget = run_budget
        self.record_dir = record_dir
        self.totals = UsageTotals()
        self.client = client or openai.AsyncOpenAI(
            base_url=base_url, api_key=api_key, timeout=120, max_retries=3
        )

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
        spec = self.role_models[role]
        sent = with_schema_instructions(messages, schema) if schema else list(messages)
        cache_id = cache_key(
            spec.id, sent, schema.__name__ if schema else None, max_tokens, temperature
        )
        cached = self.cache.get(cache_id) if self.cache else None
        if cached is not None:
            return self._finish(role, key, started, cached, cost=0.0, cached=True)
        text, tokens_in, tokens_out, cost = await self._call(
            spec, sent, schema, max_tokens, temperature
        )
        parsed = None
        if schema is not None:
            try:
                parsed = parse_model(text, schema)
            except LLMError as first:
                retry = [
                    *sent,
                    {"role": "assistant", "content": text},
                    {
                        "role": "user",
                        "content": f"Your answer was invalid ({first}). "
                        "Answer again with only the corrected JSON object.",
                    },
                ]
                text, t_in, t_out, extra = await self._call(
                    spec, retry, schema, max_tokens, temperature
                )
                tokens_in, tokens_out, cost = tokens_in + t_in, tokens_out + t_out, cost + extra
                try:
                    parsed = parse_model(text, schema)
                except LLMError as second:
                    raise LLMError(f"{key}: invalid output after retry: {second}") from second
        record = {
            "model": spec.id,
            "text": text,
            "parsed": parsed.model_dump(mode="json") if parsed else None,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }
        if self.cache:
            self.cache.put(cache_id, record)
        return self._finish(role, key, started, record, cost=cost, cached=False)

    def _finish(
        self,
        role: Role,
        key: str,
        started: float,
        record: dict[str, Any],
        *,
        cost: float,
        cached: bool,
    ) -> LLMResponse:
        usage = Usage(
            model=record["model"],
            tokens_in=record["tokens_in"],
            tokens_out=record["tokens_out"],
            cost_usd=cost,
            cached=cached,
        )
        if cached:
            self.totals.add(usage)
        if self.record_dir is not None:
            atomic_write_text(
                self.record_dir / fixture_name(key), json.dumps(record, ensure_ascii=False)
            )
        return LLMResponse(
            role=role,
            text=record["text"],
            parsed=record["parsed"],
            usage=usage,
            latency_s=time.perf_counter() - started,
        )

    async def _call(
        self,
        spec: ModelSpec,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | None,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int, int, float]:
        prompt_chars = sum(len(m["content"]) for m in messages)
        estimate = spec.cost(int(prompt_chars / CHARS_PER_TOKEN), max_tokens)
        guards = [g for g in (self.ledger, self.run_budget) if g is not None]
        reserved: list[SpendLedger | RunBudget] = []
        try:
            for guard in guards:
                await guard.reserve(estimate)
                reserved.append(guard)
            return await self._billed_call(
                spec, messages, schema, max_tokens, temperature, estimate
            )
        except BaseException:
            for guard in reserved:
                await guard.release(estimate)
            raise

    async def _billed_call(
        self,
        spec: ModelSpec,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | None,
        max_tokens: int,
        temperature: float,
        estimate: float,
    ) -> tuple[str, int, int, float]:
        kwargs: dict[str, Any] = {
            "model": spec.id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        response = await self._create(kwargs, schema)
        try:
            text = response.choices[0].message.content or ""
        except (AttributeError, IndexError) as exc:
            raise LLMError("model response has no message content") from exc
        usage = getattr(response, "usage", None)
        tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
        if usage is None or not (tokens_in or tokens_out):
            prompt_chars = sum(len(m["content"]) for m in messages)
            tokens_in, tokens_out = int(prompt_chars / CHARS_PER_TOKEN), max_tokens
        cost = spec.cost(tokens_in, tokens_out)
        self.totals.add(
            Usage(model=spec.id, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost)
        )
        for guard in (self.ledger, self.run_budget):
            if guard is not None:
                await guard.settle(estimate, cost)
        return text, tokens_in, tokens_out, cost

    async def _create(self, kwargs: dict[str, Any], schema: type[BaseModel] | None) -> Any:
        try:
            if schema is None:
                return await self.client.chat.completions.create(**kwargs)
            json_schema = {"name": schema.__name__, "schema": schema.model_json_schema()}
            structured = {"type": "json_schema", "json_schema": json_schema}
            try:
                return await self.client.chat.completions.create(
                    response_format=structured, **kwargs
                )
            except openai.BadRequestError:
                fallback = {"type": "json_object"}
                return await self.client.chat.completions.create(response_format=fallback, **kwargs)
        except openai.OpenAIError as exc:
            raise LLMError(f"Nebius request failed: {exc}") from exc
