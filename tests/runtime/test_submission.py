from __future__ import annotations

from borges.identity.principal import ANONYMOUS, Principal
from borges.identity.scopes import ADMIN, PUBLIC_SCOPES
from borges.runtime.jobs import Job
from borges.runtime.submission import may_cancel, submit_run
from tests.runtime.fake_runtime import REQUEST, make_fake_runtime

NAMED = Principal("caller://alice", "key", PUBLIC_SCOPES)
ROOT = Principal("caller://root", "key", frozenset({ADMIN}))


def job(**fields) -> Job:
    base = dict(
        run_id="r1",
        state="running",
        principal=ANONYMOUS.id,
        owner_key=f"{ANONYMOUS.id}|10.0.0.1",
        anonymous=True,
        live=False,
        source="api",
        schedule_id=None,
        request="{}",
        upload_id=None,
        dataset_name=None,
        attempts=1,
        max_attempts=3,
        not_before=0.0,
        lease_owner=None,
        lease_expires=None,
        cancel_requested=False,
        resume_reason=None,
        last_error=None,
        created_at=0.0,
        updated_at=0.0,
    )
    return Job(**{**base, **fields})


def test_an_anonymous_creator_cancels_only_from_the_same_client_session() -> None:
    assert may_cancel(job(), ANONYMOUS, "10.0.0.1") is True
    assert may_cancel(job(), ANONYMOUS, "10.0.0.2") is False


def test_anonymous_callers_never_cancel_named_runs() -> None:
    named = job(principal=NAMED.id, owner_key=NAMED.id, anonymous=False)
    assert may_cancel(named, ANONYMOUS, "10.0.0.1") is False
    assert may_cancel(named, NAMED, "anywhere") is True
    assert may_cancel(named, Principal("caller://bob", "key", PUBLIC_SCOPES), "x") is False


def test_admin_cancels_everything() -> None:
    assert may_cancel(job(), ROOT, "x") is True
    assert may_cancel(job(principal=NAMED.id, owner_key=NAMED.id, anonymous=False), ROOT, "x")


async def test_submit_creates_meta_and_job_without_starting_the_worker(
    tmp_path, monkeypatch
) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    result = await submit_run(fake.runtime, REQUEST, NAMED, "c", None, None, None, "api", None)
    assert result.created is True
    assert fake.rig.store.meta(result.run_id)["status"] == "queued"
    assert fake.runtime.queue.get(result.run_id).state == "queued"
    assert fake.rig.store.snapshot(result.run_id).status == "queued"
    assert fake.runtime.jobs == {}


async def test_a_lost_race_discards_the_provisional_run(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    key = fake.runtime.idempotency(NAMED, "c", REQUEST, "same")
    first = await submit_run(fake.runtime, REQUEST, NAMED, "c", key, None, None, "api", None)
    real_lookup = fake.runtime.queue.lookup
    fake.runtime.queue.lookup = lambda _key: None
    second = await submit_run(fake.runtime, REQUEST, NAMED, "c", key, None, None, "api", None)
    fake.runtime.queue.lookup = real_lookup
    assert second.created is False and second.run_id == first.run_id
    assert [r.run_id for r in fake.rig.store.list_runs()] == [first.run_id]
