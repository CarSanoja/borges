from __future__ import annotations

import pytest

from borges.analysis.prompts import judge
from borges.config import Settings
from borges.fleet.enforcement import RegistryBlocked, enforce_registry, unapproved
from borges.fleet.fleet import Fleet
from borges.fleet.locations import open_store
from borges.fleet.store import RegistryStore


def test_seeded_tree_has_no_blockers(fleet: Fleet, settings: Settings) -> None:
    assert unapproved(fleet, open_store(settings)) == []


def test_empty_store_blocks_every_active_agent(fleet: Fleet, empty_store: RegistryStore) -> None:
    blockers = unapproved(fleet, empty_store)
    assert len(blockers) == len(fleet.agents)
    assert {b.reason for b in blockers} == {"unpublished change"}


def test_proposed_and_retired_versions_block(fleet: Fleet, empty_store: RegistryStore) -> None:
    from borges.fleet.publish import publish_fleet

    publish_fleet(empty_store, fleet, "t")
    assert {b.reason for b in unapproved(fleet, empty_store)} == {"version 1.0.0 is proposed"}
    empty_store.transition("judge", "1.0.0", "retired", "t")
    judge_blocker = next(b for b in unapproved(fleet, empty_store) if b.agent_id == "judge")
    assert judge_blocker.reason == "version 1.0.0 is retired"


def test_live_run_blocked_when_a_prompt_changed(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    enforcing = settings.model_copy(update={"borges_registry_enforce": True})
    enforce_registry(enforcing, "nebius")
    monkeypatch.setattr(judge, "SYSTEM", judge.SYSTEM + " Be stricter.")
    with pytest.raises(RegistryBlocked) as blocked:
        enforce_registry(enforcing, "nebius")
    assert [b.agent_id for b in blocked.value.blockers] == ["judge"]
    assert "borges agents publish" in str(blocked.value)


def test_scripted_runs_and_disabled_enforcement_are_allowed(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(judge, "SYSTEM", judge.SYSTEM + " Be stricter.")
    enforcing = settings.model_copy(update={"borges_registry_enforce": True})
    enforce_registry(enforcing, "scripted")
    enforce_registry(settings, "nebius")
