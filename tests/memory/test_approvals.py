from __future__ import annotations

from borges.config import Settings
from borges.fleet.fleet import build_fleet
from borges.fleet.locations import open_store
from borges.memory.approvals import ApprovalCheck


def test_the_current_approved_definition_is_accepted(settings: Settings) -> None:
    judge = build_fleet(settings).get("judge")
    check = ApprovalCheck(settings)
    assert check.approved("judge", judge.definition_sha) is True


def test_unknown_or_missing_definitions_are_refused(settings: Settings) -> None:
    check = ApprovalCheck(settings)
    assert check.approved("judge", "deadbeef") is False
    assert check.approved("judge", None) is False
    assert check.approved(None, None) is True


def test_a_retired_version_no_longer_counts(settings: Settings) -> None:
    judge = build_fleet(settings).get("judge")
    store = open_store(settings)
    record = store.by_definition("judge", judge.definition_sha)
    store.transition("judge", record.version, "retired", "tester", "superseded")
    assert ApprovalCheck(settings).approved("judge", judge.definition_sha) is False


def test_an_unreadable_registry_fails_closed(settings: Settings, monkeypatch) -> None:
    import borges.fleet.locations as locations

    def boom(_: Settings):
        raise RuntimeError("down")

    monkeypatch.setattr(locations, "open_store", boom)
    assert ApprovalCheck(settings).approved("judge", "abc") is False
