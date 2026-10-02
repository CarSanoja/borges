from __future__ import annotations

from borges.memory.kinds import POLICIES, PUBLIC_TENANT, MemoryKind, policy_for


def test_every_kind_has_a_table_and_a_policy() -> None:
    for kind in MemoryKind:
        assert kind.table == f"memory_{kind.value}"
        policy = policy_for(kind)
        assert policy.ttl_s > 0 and policy.max_rows > 0 and policy.max_bytes > 0
    assert set(POLICIES) == set(MemoryKind)


def test_agent_kinds_name_the_agent_whose_approval_governs_them() -> None:
    assert policy_for(MemoryKind.VERDICT).agent_id == "judge"
    assert policy_for(MemoryKind.CODE).agent_id == "coder"
    assert policy_for(MemoryKind.ADVERSARY).agent_id == "adversary"
    assert policy_for(MemoryKind.NOTE).agent_id is None
    assert PUBLIC_TENANT == "public-demo"
