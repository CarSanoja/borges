from __future__ import annotations

from borges.fleet.roster import ROSTER, declaration_for
from borges.llm.client import Role


def test_roster_has_every_role_and_component() -> None:
    ids = {item.agent_id for item in ROSTER}
    assert {role.value for role in Role} <= ids
    assert {"code_guard", "harness", "smoke_tester", "garden_search", "verifier"} <= ids


def test_ids_are_unique() -> None:
    ids = [item.agent_id for item in ROSTER]
    assert len(ids) == len(set(ids))


def test_declaration_lookup() -> None:
    assert declaration_for("judge") is not None
    assert declaration_for("nobody") is None
