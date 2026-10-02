from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from borges.analysis.profile import profile_dataframe
from borges.cases.registry import CaseRegistry

CASES = Path("cases")
IDS = ["checkout_ab", "red_cards", "marp_religiosity", "marp_norms", "bank_marketing_calls"]


@pytest.mark.parametrize("case_id", IDS)
def test_every_note_names_a_real_column(case_id: str) -> None:
    registry = CaseRegistry(CASES)
    notes = registry.get(case_id).column_notes
    frame = pd.read_parquet(CASES / case_id / "data.parquet")
    assert notes
    assert set(notes) <= set(frame.columns)
    assert all(text.strip() for text in notes.values())


def test_red_cards_games_note_says_dyad() -> None:
    registry = CaseRegistry(CASES)
    note = registry.get("red_cards").column_notes["games"]
    assert "referee" in note and "not the player's total" in note


def test_profile_of_a_case_carries_its_notes() -> None:
    registry = CaseRegistry(CASES)
    frame = pd.read_parquet(CASES / "checkout_ab" / "data.parquet")
    profile = profile_dataframe(frame, "d", column_notes=registry.get("checkout_ab").column_notes)
    notes = {c.name: c.note for c in profile.columns}
    assert "treatment" in (notes["variant"] or "")
