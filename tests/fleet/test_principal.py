from __future__ import annotations

from borges.fleet.principal import agent_id_of, agent_principal


def test_principal_round_trip() -> None:
    assert agent_principal("judge") == "agent://borges/judge"
    assert agent_id_of("agent://borges/judge") == "judge"


def test_foreign_principal_has_no_agent_id() -> None:
    assert agent_id_of("user:alice") is None
    assert agent_id_of("agent://borges/") is None
