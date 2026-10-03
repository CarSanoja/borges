from __future__ import annotations

from borges.cases.registry import CaseRegistry
from borges.config import REPO_ROOT


def test_every_case_declares_where_its_data_comes_from() -> None:
    cards = CaseRegistry(REPO_ROOT / "cases").list()
    assert cards
    for card in cards:
        label = card.provenance.lower()
        assert label.startswith(("synthetic", "real data")), card.id
        if label.startswith("real data"):
            assert any(tag in label for tag in ("cc0", "cc by", "odc-by")), card.id
