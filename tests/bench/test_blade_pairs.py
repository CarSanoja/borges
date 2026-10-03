from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.bench.blade_pairs import MatchPair, parse_pairs
from borges.llm.client import LLMError

REPLIES = Path(__file__).parent / "fixtures" / "blade_replies"


def reply(name: str) -> str:
    return json.loads((REPLIES / name).read_text(encoding="utf-8"))["text"]


def triples(pairs: list[MatchPair]) -> list[tuple[int, int, int]]:
    return [(p.expert, p.agent, p.similarity) for p in pairs]


def test_well_formed_reply_from_the_live_run_is_parsed() -> None:
    pairs = parse_pairs(reply("soccer_well_formed.json"), n_expert=16, n_agent=15)
    assert triples(pairs) == [(0, 0, 10), (1, 1, 10), (6, 2, 10)]


def test_keys_with_a_leading_counter_and_joined_labels_are_read_by_letter() -> None:
    pairs = parse_pairs(reply("soccer_bare_numbers.json"), n_expert=16, n_agent=15)
    assert triples(pairs) == [(0, 0, 10), (1, 1, 10), (6, 2, 10)]


def test_labels_decide_the_side_not_the_order_of_the_key() -> None:
    pairs = parse_pairs(reply("panda_nuts_swapped_letters.json"), n_expert=8, n_agent=8)
    assert (1, 0, 10) in triples(pairs) and (2, 2, 10) in triples(pairs)
    assert (5, 3, 10) in triples(pairs) and (4, 4, 10) in triples(pairs)


def test_one_key_naming_several_a_items_matches_each_of_them() -> None:
    text = '{"A3-A5-B3": {"rationale": "x", "similarity": 8}}'
    pairs = parse_pairs(text, n_expert=6, n_agent=4)
    assert triples(pairs) == [(2, 2, 8), (4, 2, 8)]


def test_placeholder_keys_and_empty_entries_are_dropped() -> None:
    pairs = parse_pairs(reply("fish_question_mark_keys.json"), n_expert=5, n_agent=5)
    assert triples(pairs) == [(0, 1, 8), (4, 4, 8)]


def test_float_and_text_similarities_are_tolerated() -> None:
    text = json.dumps(
        {
            "A1-B1": {"similarity": 8.5},
            "A2-B2": {"similarity": "9"},
            "A3-B3": {"similarity": "high"},
        }
    )
    assert triples(parse_pairs(text, 3, 3)) == [(0, 0, 8), (1, 1, 9)]


def test_empty_object_is_an_empty_answer() -> None:
    assert parse_pairs(reply("affairs_empty.json"), n_expert=5, n_agent=2) == []


def test_two_bare_numbers_still_mean_expert_then_agent() -> None:
    assert triples(parse_pairs('{"1-2": {"similarity": 9}}', 2, 2)) == [(0, 1, 9)]


def test_truncated_reply_is_an_error_not_an_empty_answer() -> None:
    with pytest.raises(LLMError):
        parse_pairs(reply("teaching_truncated_multi_a.json"), n_expert=18, n_agent=12)
