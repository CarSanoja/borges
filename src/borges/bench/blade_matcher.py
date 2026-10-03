from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pydantic import RootModel

from borges.bench.blade_prompts import SYSTEM, user_message
from borges.llm.cache import DiskCache, cache_key
from borges.llm.client import KNOWN_MODELS, SUPER, ModelSpec
from borges.llm.json_output import parse_model

CHUNK = 40
MATCH_THRESHOLD = 8
PAIR = re.compile(r"\d+")


class MatchTable(RootModel[dict[str, Any]]):
    pass


@dataclass(frozen=True)
class MatchPair:
    expert: int
    agent: int
    similarity: int


@dataclass
class MatcherUsage:
    calls: int = 0
    cached_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


class Matcher(Protocol):
    name: str
    usage: MatcherUsage

    async def match(
        self, kind: str, question: str, schema: str, expert: list[str], agent: list[str]
    ) -> list[MatchPair]: ...


def parse_pairs(text: str, n_expert: int, n_agent: int, offset: int = 0) -> list[MatchPair]:
    table = parse_model(text, MatchTable).root
    pairs: list[MatchPair] = []
    for key, value in table.items():
        numbers = PAIR.findall(key)
        if len(numbers) != 2 or not isinstance(value, dict):
            continue
        left, right = int(numbers[0]) - 1, int(numbers[1]) - 1
        try:
            similarity = int(value.get("similarity", 10))
        except (TypeError, ValueError):
            continue
        if 0 <= left < n_expert and 0 <= right < n_agent:
            pairs.append(MatchPair(left, right + offset, similarity))
    return pairs


@dataclass
class LLMMatcher:
    client: Any
    model: ModelSpec = field(default_factory=lambda: SUPER)
    cache: DiskCache | None = None
    usage: MatcherUsage = field(default_factory=MatcherUsage)

    @property
    def name(self) -> str:
        return f"llm:{self.model.id}"

    async def _ask(self, messages: list[dict[str, str]]) -> str:
        key = cache_key(self.model.id, messages, "match", 2000, 0.0)
        cached = self.cache.get(key) if self.cache else None
        self.usage.calls += 1
        if cached is not None:
            self.usage.cached_calls += 1
            return str(cached["text"])
        reply = await self.client.chat.completions.create(
            model=self.model.id,
            messages=messages,
            max_tokens=2000,
            temperature=0.0,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        text = reply.choices[0].message.content or ""
        used = reply.usage
        tokens_in, tokens_out = (used.prompt_tokens, used.completion_tokens) if used else (0, 0)
        self.usage.tokens_in += tokens_in
        self.usage.tokens_out += tokens_out
        self.usage.cost_usd += self.model.cost(tokens_in, tokens_out)
        if self.cache:
            self.cache.put(key, {"text": text, "tokens_in": tokens_in, "tokens_out": tokens_out})
        return text

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
            pairs.extend(parse_pairs(await self._ask(messages), len(expert), len(chunk), start))
        return pairs


def make_llm_matcher(
    api_key: str, base_url: str, model_id: str | None, cache_dir: Path
) -> LLMMatcher:
    import openai

    model = KNOWN_MODELS.get(model_id or SUPER.id) or ModelSpec(
        id=model_id or SUPER.id,
        input_usd_per_m=SUPER.input_usd_per_m,
        output_usd_per_m=SUPER.output_usd_per_m,
    )
    return LLMMatcher(
        openai.AsyncOpenAI(api_key=api_key, base_url=base_url), model, DiskCache(cache_dir)
    )
