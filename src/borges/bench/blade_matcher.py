from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from borges.bench.blade_pairs import MatchPair, parse_pairs
from borges.bench.blade_prompts import SYSTEM, user_message
from borges.llm.cache import DiskCache, cache_key
from borges.llm.client import KNOWN_MODELS, SUPER, LLMError, ModelSpec

CHUNK = 40
MAX_TOKENS = 4000
MATCH_THRESHOLD = 8


class MissingReply(RuntimeError):
    pass


@dataclass
class MatcherUsage:
    calls: int = 0
    cached_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    failed_chunks: int = 0


class Matcher(Protocol):
    name: str
    usage: MatcherUsage

    async def match(
        self, kind: str, question: str, schema: str, expert: list[str], agent: list[str]
    ) -> list[MatchPair]: ...


@dataclass
class LLMMatcher:
    client: Any
    model: ModelSpec = field(default_factory=lambda: SUPER)
    cache: DiskCache | None = None
    usage: MatcherUsage = field(default_factory=MatcherUsage)

    @property
    def name(self) -> str:
        return f"llm:{self.model.id}"

    async def _ask(self, messages: list[dict[str, str]]) -> tuple[str, str | None]:
        key = cache_key(self.model.id, messages, "match-json", MAX_TOKENS, 0.0)
        cached = self.cache.get(key) if self.cache else None
        self.usage.calls += 1
        if cached is not None:
            self.usage.cached_calls += 1
            return str(cached["text"]), None
        reply = await self.client.chat.completions.create(
            model=self.model.id,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.0,
            response_format={"type": "json_object"},
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        text = reply.choices[0].message.content or ""
        used = reply.usage
        tokens_in, tokens_out = (used.prompt_tokens, used.completion_tokens) if used else (0, 0)
        self.usage.tokens_in += tokens_in
        self.usage.tokens_out += tokens_out
        self.usage.cost_usd += self.model.cost(tokens_in, tokens_out)
        return text, key

    def _remember(self, key: str | None, text: str) -> None:
        if self.cache and key:
            self.cache.put(key, {"text": text})

    async def _chunk(
        self, messages: list[dict[str, str]], n_expert: int, n_agent: int, offset: int
    ) -> list[MatchPair]:
        for _ in range(2):
            text, key = await self._ask(messages)
            try:
                pairs = parse_pairs(text, n_expert, n_agent, offset)
            except LLMError as exc:
                messages = [
                    *messages,
                    {"role": "assistant", "content": text[:6000]},
                    {"role": "user", "content": f"{exc}. Return only the corrected JSON object."},
                ]
                continue
            self._remember(key, text)
            return pairs
        self.usage.failed_chunks += 1
        return []

    async def match(
        self, kind: str, question: str, schema: str, expert: list[str], agent: list[str]
    ) -> list[MatchPair]:
        pairs: list[MatchPair] = []
        for start in range(0, len(agent), CHUNK):
            chunk = agent[start : start + CHUNK]
            messages = [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_message(kind, question, schema, expert, chunk)},
            ]
            pairs.extend(await self._chunk(messages, len(expert), len(chunk), start))
        return pairs


def make_llm_matcher(
    api_key: str, base_url: str, model_id: str | None, cache_dir: Path
) -> LLMMatcher:
    from borges.llm.nebius_provider import NebiusLLM

    model = KNOWN_MODELS.get(model_id or SUPER.id) or ModelSpec(
        id=model_id or SUPER.id,
        input_usd_per_m=SUPER.input_usd_per_m,
        output_usd_per_m=SUPER.output_usd_per_m,
    )
    provider = NebiusLLM(api_key=api_key, base_url=base_url)
    return LLMMatcher(provider.client, model, DiskCache(cache_dir))
