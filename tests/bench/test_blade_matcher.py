from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from borges.bench.blade_lexical import LexicalMatcher
from borges.bench.blade_matcher import CHUNK, LLMMatcher, parse_pairs
from borges.bench.blade_prompts import ATTRIBUTION, user_message
from borges.llm.cache import DiskCache
from borges.llm.client import SUPER


class FakeCompletions:
    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        text = self.replies[len(self.calls) - 1]
        usage = SimpleNamespace(prompt_tokens=1000, completion_tokens=200)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=text))], usage=usage
        )


def client(replies: list[str]):
    completions = FakeCompletions(replies)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def test_pairs_are_parsed_and_out_of_range_ones_dropped() -> None:
    text = '```json\n{"A1-B2": {"similarity": 9}, "A9-B1": {"similarity": 9}, "A2-B1": {}}\n```'
    pairs = parse_pairs(text, n_expert=2, n_agent=2, offset=10)
    assert [(p.expert, p.agent, p.similarity) for p in pairs] == [(0, 11, 9), (1, 10, 10)]


def test_prompt_numbers_both_lists_and_names_the_question() -> None:
    message = user_message("cvar", "Does X cause Y?", "col: desc", ["IV: x"], ["IV: z", "DV: w"])
    assert "Does X cause Y?" in message and '"1": ' in message and '"2": ' in message
    assert "similarity" in message and "BLADE" in ATTRIBUTION


async def test_llm_matcher_prices_calls_and_caches(tmp_path) -> None:
    fake, completions = client(['{"A1-B1": {"similarity": 9}}'])
    matcher = LLMMatcher(fake, SUPER, DiskCache(tmp_path))
    first = await matcher.match("model", "q", "s", ["linear"], ["ols"])
    again = await matcher.match("model", "q", "s", ["linear"], ["ols"])
    assert first == again and len(completions.calls) == 1
    assert matcher.usage.calls == 2 and matcher.usage.cached_calls == 1
    assert matcher.usage.cost_usd == pytest.approx(SUPER.cost(1000, 200))
    call = completions.calls[0]
    assert call["model"] == SUPER.id and call["temperature"] == 0.0
    assert call["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}


async def test_long_agent_lists_are_matched_in_chunks() -> None:
    agent = [f"item {i}" for i in range(CHUNK + 5)]
    fake, completions = client(['{"A1-B3": {"similarity": 9}}', '{"A1-B2": {"similarity": 8}}'])
    matcher = LLMMatcher(fake, SUPER)
    pairs = await matcher.match("transform", "q", "s", ["drop rows"], agent)
    assert len(completions.calls) == 2
    assert sorted((p.agent, p.similarity) for p in pairs) == [(2, 9), (CHUNK + 1, 8)]


async def test_lexical_matcher_is_labelled_as_plumbing() -> None:
    matcher = LexicalMatcher()
    pairs = await matcher.match(
        "cvar", "q", "s", ["IV: femininity of hurricane name"], ["IV: hurricane name femininity"]
    )
    assert pairs and pairs[0].similarity >= 8
    assert "not a BLADE score" in matcher.name
    assert json.dumps(matcher.name)


async def test_invalid_json_is_retried_once_and_not_cached(tmp_path) -> None:
    fake, completions = client(["{'A1-B1': 9,", '{"A1-B1": {"similarity": 9}}'])
    matcher = LLMMatcher(fake, SUPER, DiskCache(tmp_path))
    pairs = await matcher.match("model", "q", "s", ["linear"], ["ols"])
    assert [(p.expert, p.agent) for p in pairs] == [(0, 0)]
    assert len(completions.calls) == 2 and matcher.usage.failed_chunks == 0
    assert "corrected JSON" in completions.calls[1]["messages"][-1]["content"]
    assert completions.calls[0]["response_format"] == {"type": "json_object"}


async def test_two_invalid_replies_score_the_chunk_as_unmatched() -> None:
    fake, completions = client(["not json", "still not json"])
    matcher = LLMMatcher(fake, SUPER)
    pairs = await matcher.match("model", "q", "s", ["linear"], ["ols"])
    assert pairs == [] and matcher.usage.failed_chunks == 1 and len(completions.calls) == 2
