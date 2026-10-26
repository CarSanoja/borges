"""Budgeted Anthropic transport for the separate validation harness."""

from __future__ import annotations

from pathlib import Path

import httpx

from borges.llm.cache import DiskCache
from borges.llm.client import LLMError, ModelSpec, Role, Usage
from borges.llm.nebius_provider import NebiusLLM
from borges.llm.nebius_transport import TruncatedOutput
from borges.llm.spend import RunBudget, SpendLedger
from borges.telemetry.redaction import redact_text

HAIKU = ModelSpec(id="claude-haiku-5-5", input_usd_per_m=0.10, output_usd_per_m=0.50)


class HaikuValidationLLM(NebiusLLM):
    def __init__(
        self,
        api_key: str,
        home: Path,
        cap: float,
        total_cap: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        client = client or httpx.AsyncClient(
            base_url="https://api.anthropic.com/v1/",
            headers={"Authorization": f"Bearer {api_key}", "anthropic-version": "2023-06-01"},
            timeout=120,
        )
        super().__init__(
            api_key=api_key,
            base_url="https://api.anthropic.com/v1/",
            role_models={role: HAIKU for role in Role},
            cache=DiskCache(home / "cache-no-thinking-v1"),
            ledger=SpendLedger(home / "spend.json", total_cap),
            run_budget=RunBudget(cap),
            client=client,
        )

    async def _billed_call(self, spec, messages, schema, max_tokens, temperature, estimate):
        if sum(len(message["content"]) for message in messages) > 50_000:
            raise LLMError("Haiku validation prompt exceeds its small-context limit")
        payload = {
            "model": HAIKU.id,
            "system": "\n\n".join(m["content"] for m in messages if m["role"] == "system"),
            "messages": [m for m in messages if m["role"] != "system"],
            "max_tokens": max_tokens,
            "thinking": {"type": "disabled"},
        }
        try:
            response = await self.client.post("messages", json=payload)
        except httpx.HTTPError as exc:
            raise LLMError(f"Anthropic transport failed: {type(exc).__name__}") from exc
        if response.status_code != 200:
            try:
                detail = redact_text(response.json().get("error", {}).get("message", ""))
            except ValueError:
                detail = "no JSON error detail"
            raise LLMError(f"Anthropic returned HTTP {response.status_code}: {detail}")
        raw = response.json()
        usage = raw["usage"]
        tokens_in = usage["input_tokens"]
        tokens_out = usage["output_tokens"]
        cost = HAIKU.cost(tokens_in, tokens_out)
        if tokens_in > 100_000:
            cost *= 5
        self.totals.add(
            Usage(model=raw["model"], tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost)
        )
        for guard in (self.ledger, self.run_budget):
            if guard is not None:
                await guard.settle(estimate, cost)
        if raw.get("stop_reason") == "max_tokens":
            raise TruncatedOutput("Haiku validation output reached max_tokens")
        text = "".join(block.get("text", "") for block in raw["content"])
        return text, tokens_in, tokens_out, cost
