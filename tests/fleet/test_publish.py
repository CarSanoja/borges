from __future__ import annotations

import pytest

from borges.analysis.prompts import judge
from borges.config import Settings
from borges.fleet.fleet import Fleet, build_fleet
from borges.fleet.publish import publish_fleet
from borges.fleet.store import RegistryStore


def test_first_publish_records_every_agent(fleet: Fleet, empty_store: RegistryStore) -> None:
    published = publish_fleet(empty_store, fleet, "tester")
    assert len(published) == len(fleet.agents)
    assert {p.version for p in published} == {"1.0.0"}
    assert {r.state for r in empty_store.records()} == {"proposed"}


def test_second_publish_is_a_no_op(fleet: Fleet, empty_store: RegistryStore) -> None:
    publish_fleet(empty_store, fleet, "tester")
    assert publish_fleet(empty_store, fleet, "tester") == []
    assert len(empty_store.events()) == len(fleet.agents)


def test_prompt_change_bumps_minor_only_for_that_agent(
    settings: Settings, fleet: Fleet, empty_store: RegistryStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    publish_fleet(empty_store, fleet, "tester")
    monkeypatch.setattr(judge, "SYSTEM", judge.SYSTEM + " Be stricter.")
    published = publish_fleet(empty_store, build_fleet(settings), "tester", "tighten judge")
    assert [(p.agent_id, p.version, p.bump) for p in published] == [("judge", "1.1.0", "minor")]
    assert "prompt_sha" in published[0].changelog and "tighten judge" in published[0].changelog


def test_capability_change_bumps_major(
    settings: Settings, fleet: Fleet, empty_store: RegistryStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    publish_fleet(empty_store, fleet, "tester")
    from borges.fleet import roster_agents

    judge_declaration = next(d for d in roster_agents.AGENT_DECLARATIONS if d.agent_id == "judge")
    widened = type(judge_declaration)(
        **{
            **judge_declaration.__dict__,
            "capabilities": (*judge_declaration.capabilities, "sandbox.exec"),
        }
    )
    monkeypatch.setattr(
        "borges.fleet.fleet.ROSTER",
        tuple(widened if d.agent_id == "judge" else d for d in roster_agents.AGENT_DECLARATIONS),
    )
    published = publish_fleet(empty_store, build_fleet(settings), "tester")
    assert [(p.agent_id, p.version, p.bump) for p in published] == [("judge", "2.0.0", "major")]
    assert "capabilities +sandbox.exec" in published[0].changelog
