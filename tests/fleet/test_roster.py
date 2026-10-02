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


def test_every_declaration_hashes_files_that_exist() -> None:
    from borges.fleet.fingerprints import PACKAGE_ROOT

    for item in ROSTER:
        assert item.code_files, item.agent_id
        for pattern in item.code_files:
            assert list(PACKAGE_ROOT.glob(pattern)), (item.agent_id, pattern)


def test_user_prompt_builders_are_part_of_the_agent_definition() -> None:
    patterns = {p for item in ROSTER if item.kind == "agent" for p in item.code_files}
    for role in ("planner", "coder", "adversary", "judge", "reviewer", "narrator"):
        assert (
            f"analysis/prompts/{role}.py" in patterns or f"analysis/prompts/{role}*.py" in patterns
        )
