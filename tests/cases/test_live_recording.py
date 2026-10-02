from __future__ import annotations

from pathlib import Path

import pytest

from borges.cases.registry import CaseRegistry
from tests.live_cases import LIVE_RUN_ID, make_cases_dir


def test_card_without_live_recording_has_no_summary(tmp_path: Path) -> None:
    registry = CaseRegistry(make_cases_dir(tmp_path, live=False))
    card = registry.card("checkout_ab")
    assert card.live_recording is None
    assert card.has_recording is True
    assert registry.recording("checkout_ab", "live") is None


def test_live_summary_is_computed_from_the_sample(tmp_path: Path) -> None:
    registry = CaseRegistry(make_cases_dir(tmp_path))
    card = registry.card("checkout_ab")
    live = card.live_recording
    assert live is not None
    assert live.recorded_at == "2026-10-02T11:11:56Z"
    assert live.models["narrator"] == "nvidia/Nemotron-3-Ultra-550b-a55b"
    assert live.models["coder"] == "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
    assert (live.llm_calls, live.tokens_in, live.tokens_out) == (22, 33499, 9371)
    assert live.cost_usd == pytest.approx(0.0069732)
    assert live.verdict == "DON'T SHIP"
    assert live.flipped_verdict == "SHIP"
    assert live.flip_kind == "direction"
    assert live.universes == 8


def test_sources_are_separate_and_default_is_scripted(tmp_path: Path) -> None:
    registry = CaseRegistry(make_cases_dir(tmp_path))
    live = registry.recording("checkout_ab", "live")
    scripted = registry.recording("checkout_ab")
    assert live is not None and live[0].run_id == LIVE_RUN_ID
    assert scripted is not None and scripted[0].run_id != LIVE_RUN_ID
    assert registry.recording("checkout_ab", "scripted") == scripted


def test_live_only_case_with_a_live_recording_is_listed_with_summary(tmp_path: Path) -> None:
    registry = CaseRegistry(make_cases_dir(tmp_path, scripted=False, live_only=True))
    card = registry.list()[0]
    assert card.live_only is True
    assert card.has_recording is False
    assert card.live_recording is not None


def test_unknown_source_is_rejected(tmp_path: Path) -> None:
    registry = CaseRegistry(make_cases_dir(tmp_path))
    with pytest.raises(ValueError):
        registry.recording("checkout_ab", "other")
