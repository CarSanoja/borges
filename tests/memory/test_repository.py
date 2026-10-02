from __future__ import annotations

import pytest

from borges.memory.entry import MemoryEntry
from borges.memory.kinds import KindPolicy, MemoryKind
from borges.memory.repository import MemoryRepository, MemoryUnavailable


def entry(signature: str = "s1", kind: MemoryKind = MemoryKind.VERDICT, **payload) -> MemoryEntry:
    return MemoryEntry(
        kind,
        "ds1",
        "fam1",
        signature,
        payload or {"text": "hello"},
        run_id="r1",
        agent_id="judge",
        agent_version="1.0.0",
        definition_sha="abc",
    )


def test_put_then_load_round_trips_with_provenance(repo: MemoryRepository) -> None:
    repo.put("acme", entry())
    loaded = repo.load("acme", MemoryKind.VERDICT, "ds1")
    assert [e.signature for e in loaded.entries] == ["s1"]
    found = loaded.entries[0]
    assert found.payload == {"text": "hello"}
    assert (found.run_id, found.agent_id, found.agent_version) == ("r1", "judge", "1.0.0")


def test_tenant_a_cannot_read_what_tenant_b_stored(repo: MemoryRepository) -> None:
    repo.put("tenant-b", entry(secret="b-only"))
    assert repo.load("tenant-a", MemoryKind.VERDICT, "ds1").entries == []
    assert repo.load("tenant-a", MemoryKind.VERDICT, "ds1", "fam1").entries == []
    assert repo.counts("tenant-a") == []
    assert repo.forget("tenant-a") == {"verdict": 0, "code": 0, "adversary": 0, "note": 0}
    assert len(repo.load("tenant-b", MemoryKind.VERDICT, "ds1").entries) == 1


def test_the_same_signature_is_kept_apart_per_tenant(repo: MemoryRepository) -> None:
    repo.put("a", entry(text="a"))
    repo.put("b", entry(text="b"))
    assert repo.load("a", MemoryKind.VERDICT, "ds1").entries[0].payload == {"text": "a"}
    assert repo.load("b", MemoryKind.VERDICT, "ds1").entries[0].payload == {"text": "b"}


@pytest.mark.parametrize("tenant", ["", "   "])
def test_every_query_requires_a_tenant(repo: MemoryRepository, tenant: str) -> None:
    for call in (
        lambda: repo.load(tenant, MemoryKind.VERDICT, "ds1"),
        lambda: repo.put(tenant, entry()),
        lambda: repo.counts(tenant),
        lambda: repo.forget(tenant),
        lambda: repo.touch(tenant, MemoryKind.CODE, [1]),
    ):
        with pytest.raises(ValueError):
            call()


def test_a_row_moved_to_another_tenant_cannot_be_decrypted(repo: MemoryRepository) -> None:
    repo.put("a", entry())
    repo.conn.execute("UPDATE memory_verdict SET tenant = 'b'")
    repo.conn.commit()
    loaded = repo.load("b", MemoryKind.VERDICT, "ds1")
    assert loaded.entries == [] and loaded.unreadable == 1


def test_payloads_are_encrypted_at_rest(repo: MemoryRepository) -> None:
    repo.put("acme", entry(text="the revenue column is in cents"))
    blob = repo.conn.execute("SELECT payload FROM memory_verdict").fetchone()[0]
    assert b"revenue" not in bytes(blob)


def test_named_tenants_are_refused_without_a_key(plain_repo: MemoryRepository) -> None:
    assert plain_repo.storable("acme") is False
    with pytest.raises(MemoryUnavailable):
        plain_repo.put("acme", entry())
    assert plain_repo.put("public-demo", entry()) is True
    stored = plain_repo.conn.execute("SELECT payload FROM memory_verdict").fetchone()[0]
    assert b"hello" in bytes(stored)
    assert len(plain_repo.load("public-demo", MemoryKind.VERDICT, "ds1").entries) == 1


def test_expired_rows_are_not_loaded_and_are_purged_on_write(repo: MemoryRepository) -> None:
    now = [1000.0]
    repo.clock = lambda: now[0]
    repo.put("acme", entry("old"))
    now[0] += 91 * 86400
    assert repo.load("acme", MemoryKind.VERDICT, "ds1").entries == []
    repo.put("acme", entry("new"))
    rows = repo.conn.execute("SELECT signature FROM memory_verdict").fetchall()
    assert [r["signature"] for r in rows] == ["new"]


def test_ttl_differs_per_kind(repo: MemoryRepository) -> None:
    now = [1000.0]
    repo.clock = lambda: now[0]
    repo.put("acme", entry("v", MemoryKind.VERDICT, text="x"))
    repo.put("acme", entry("c", MemoryKind.CODE, code="x"))
    now[0] += 45 * 86400
    assert len(repo.load("acme", MemoryKind.VERDICT, "ds1").entries) == 1
    assert repo.load("acme", MemoryKind.CODE, "ds1").entries == []


def test_row_cap_evicts_the_least_recently_used(
    repo: MemoryRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    from borges.memory import repository

    monkeypatch.setattr(
        repository,
        "policy_for",
        lambda kind: KindPolicy(ttl_s=1e9, max_rows=2, max_bytes=10**9, agent_id=None),
    )
    now = [1.0]
    repo.clock = lambda: now[0]
    for index, name in enumerate(("a", "b")):
        now[0] = float(index + 1)
        repo.put("acme", entry(name))
    now[0] = 10.0
    first = repo.load("acme", MemoryKind.VERDICT, "ds1").entries[0]
    repo.touch("acme", MemoryKind.VERDICT, [first.row_id])
    now[0] = 11.0
    repo.put("acme", entry("c"))
    kept = {e.signature for e in repo.load("acme", MemoryKind.VERDICT, "ds1").entries}
    assert kept == {"a", "c"}


def test_byte_cap_evicts_even_below_the_row_cap(
    repo: MemoryRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    from borges.memory import repository

    monkeypatch.setattr(
        repository,
        "policy_for",
        lambda kind: KindPolicy(ttl_s=1e9, max_rows=100, max_bytes=400, agent_id=None),
    )
    for index in range(6):
        repo.clock = lambda i=index: float(i)
        repo.put("acme", entry(f"s{index}", text="x" * 150))
    assert len(repo.load("acme", MemoryKind.VERDICT, "ds1").entries) <= 2


def test_oversized_payloads_are_not_stored(repo: MemoryRepository) -> None:
    assert repo.put("acme", entry(text="x" * 70_000)) is False


def test_family_load_reaches_sibling_datasets(repo: MemoryRepository) -> None:
    sibling = entry("s2")
    sibling.dataset_fp = "ds2"
    repo.put("acme", entry("s1"))
    repo.put("acme", sibling)
    assert len(repo.load("acme", MemoryKind.VERDICT, "ds1").entries) == 1
    assert len(repo.load("acme", MemoryKind.VERDICT, "ds1", "fam1").entries) == 2


def test_counts_list_per_dataset_without_payloads(repo: MemoryRepository) -> None:
    repo.put("acme", entry("s1"))
    repo.put("acme", entry("s2", MemoryKind.CODE, code="x"))
    (row,) = repo.counts("acme")
    assert row["dataset"] == "ds1"
    assert (row["verdict"], row["code"], row["adversary"], row["note"]) == (1, 1, 0, 0)
    assert "payload" not in row


def test_forget_one_dataset_or_everything(repo: MemoryRepository) -> None:
    other = entry("s2")
    other.dataset_fp = "ds2"
    repo.put("acme", entry("s1"))
    repo.put("acme", other)
    assert repo.forget("acme", "ds1")["verdict"] == 1
    assert [r["dataset"] for r in repo.counts("acme")] == ["ds2"]
    assert repo.forget("acme")["verdict"] == 1
    assert repo.counts("acme") == []


def test_rewriting_a_signature_replaces_it_and_keeps_hits(repo: MemoryRepository) -> None:
    repo.put("acme", entry(text="one"))
    row = repo.load("acme", MemoryKind.VERDICT, "ds1").entries[0]
    repo.touch("acme", MemoryKind.VERDICT, [row.row_id])
    repo.put("acme", entry(text="two"))
    again = repo.load("acme", MemoryKind.VERDICT, "ds1").entries
    assert len(again) == 1 and again[0].payload == {"text": "two"} and again[0].hits == 1
