from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import openai
from pydantic import BaseModel

from borges.llm.cache import DiskCache, cache_key
from borges.llm.client import (
    DEFAULT_ROLE_MODELS,
    LLMError,
    LLMResponse,
    ModelSpec,
    Role,
    Usage,
    UsageTotals,
)
from borges.llm.json_output import parse_model
from borges.llm.nebius_response import read_completion, with_reservation, write_fixture
from borges.llm.nebius_transport import (
    TruncatedOutput,
    create_completion,
    estimate_prompt_tokens,
    nebius_thinking_body,
    retry_messages,
    with_schema_instructions,
)
from borges.llm.spend import RunBudget, SpendLedger


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
        thinking_body: Callable[[bool], dict[str, Any]] = nebius_thinking_body,
        retry_truncated_without_thinking: bool = False,
    ) -> None:
        self.retry_truncated_without_thinking = retry_truncated_without_thinking
        self.thinking_body = thinking_body
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
        started, spec = time.perf_counter(), self.role_models[role]
        sent = with_schema_instructions(messages, schema) if schema else list(messages)
        cache_id = cache_key(
            spec.id, sent, schema.__name__ if schema else None, max_tokens, temperature
        )
        cached = self.cache.get(cache_id) if self.cache else None
        if cached is not None:
            return self._finish(role, key, started, cached, cost=0.0, cached=True)
        text, tokens_in, tokens_out, cost = await self._call_keyed(
            key, spec, sent, schema, max_tokens, temperature
        )
        parsed = None
        if schema is not None:
            try:
                parsed = parse_model(text, schema)
            except LLMError as first:
                retry = retry_messages(sent, text, first)
                text, t_in, t_out, extra = await self._call_keyed(
                    key, spec, retry, schema, max_tokens, temperature
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
            "latency_s": round(time.perf_counter() - started, 3),
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
            write_fixture(self.record_dir, key, record)
        return LLMResponse(
            role=role,
            text=record["text"],
            parsed=record["parsed"],
            usage=usage,
            latency_s=time.perf_counter() - started,
        )

    async def _call_keyed(
        self,
        key: str,
        spec: ModelSpec,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | None,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int, int, float]:
        try:
            return await self._call(spec, messages, schema, max_tokens, temperature)
        except TruncatedOutput as exc:
            if not (self.retry_truncated_without_thinking and spec.thinking):
                raise LLMError(f"{key}: output truncated at max_tokens") from exc
        quiet = spec.model_copy(update={"thinking": False})
        try:
            return await self._call(quiet, messages, schema, max_tokens, temperature)
        except TruncatedOutput as exc:
            raise LLMError(f"{key}: output truncated at max_tokens") from exc

    async def _call(
        self,
        spec: ModelSpec,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | None,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int, int, float]:
        estimate = spec.cost(estimate_prompt_tokens(messages), max_tokens)

        def call() -> Awaitable[tuple[str, int, int, float]]:
            return self._billed_call(spec, messages, schema, max_tokens, temperature, estimate)

        return await with_reservation((self.ledger, self.run_budget), estimate, call)

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
            "extra_body": self.thinking_body(spec.thinking),
        }
        response = await create_completion(self.client, kwargs, schema)
        text, tokens_in, tokens_out, truncated = read_completion(response, messages, max_tokens)
        cost = spec.cost(tokens_in, tokens_out)
        self.totals.add(
            Usage(model=spec.id, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost)
        )
        for guard in (self.ledger, self.run_budget):
            if guard is not None:
                await guard.settle(estimate, cost)
        if truncated:
            raise TruncatedOutput("output truncated at max_tokens")
        return text, tokens_in, tokens_out, cost
