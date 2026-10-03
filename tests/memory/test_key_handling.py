from __future__ import annotations

import logging

import pytest

from borges.config import Settings
from borges.memory import service
from borges.memory.kinds import MemoryKind
from borges.memory.tenant import resolve_mode
from tests.memory.plans import profile
from tests.memory.sessions import make_session

FP = "c" * 64


def seeded(settings: Settings) -> None:
    session = make_session(settings, run_id="r_old")
    session.attach(profile())
    assert session.stage(MemoryKind.VERDICT, "sig", {"ctx": "c", "text": "t", "reason": "fine"})
    session.flush()
    session.repo.close()


def test_named_tenants_are_not_remembered_without_a_key(settings: Settings) -> None:
    keyless = settings.model_copy(update={"borges_memory_key": None})
    mode = resolve_mode(keyless, "caller://acme")
    assert mode.enabled is False and "BORGES_MEMORY_KEY" in (mode.reason or "")


def test_a_wrong_key_fails_closed_with_a_warning(
    settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    seeded(settings)
    wrong = settings.model_copy(update={"borges_memory_key": "w" * 32})
    session = make_session(wrong)
    session.attach(profile())
    with caplog.at_level(logging.WARNING, logger="borges.memory"):
        assert session.find(MemoryKind.VERDICT, "sig") is None
    assert session.usage()["dropped"] == 1
    assert any("wrong or rotated" in r.getMessage() for r in caplog.records)
    assert "w" * 32 not in caplog.text


def test_no_key_at_all_reads_nothing_of_an_encrypted_named_tenant(settings: Settings) -> None:
    seeded(settings)
    keyless = settings.model_copy(update={"borges_memory_key": None})
    session = make_session(keyless)
    assert session.find(MemoryKind.VERDICT, "sig") is None


def test_the_right_key_still_reads_it(settings: Settings) -> None:
    seeded(settings)
    session = make_session(settings)
    session.attach(profile())
    assert session.find(MemoryKind.VERDICT, "sig") is not None


def test_a_keyed_run_does_not_reveal_the_dataset_fingerprint(settings: Settings) -> None:
    session = make_session(settings)
    session.attach(profile())
    assert session.usage()["dataset"] == ""
    public = make_session(settings, principal=None)
    public.attach(profile())
    assert len(public.usage()["dataset"]) == 12


def test_anonymous_callers_see_nothing_of_a_named_tenant(settings: Settings) -> None:
    session = make_session(settings, run_id="r_old")
    session.attach(profile())
    session.stage(MemoryKind.VERDICT, "sig", {"ctx": "c", "text": "t", "reason": "fine"})
    session.flush()
    session.repo.close()
    seen = service.describe(settings, None)
    assert seen["tenant"] == "public-demo"
    assert seen["datasets"] == [] and sum(seen["totals"].values()) == 0
    assert session.dataset_fp not in str(seen)
    assert service.describe(settings, "caller://acme")["totals"]["verdict"] == 1
