from __future__ import annotations

from borges.armor.report import ArmorReport
from borges.config import Settings
from borges.memory.factory import build_run_memory, open_repository
from borges.memory.kinds import MemoryKind
from tests.memory.plans import profile


def build(settings: Settings, principal: str | None, curated: bool = True, reads: bool = True):
    return build_run_memory(settings, principal, "r_1", None, ArmorReport(), curated, reads)


def test_the_repository_is_encrypted_when_the_key_is_set(settings: Settings) -> None:
    assert open_repository(settings).sealer.encrypted is True
    assert (
        open_repository(settings.model_copy(update={"borges_memory_key": None})).sealer.encrypted
        is False
    )


def test_a_run_memory_is_built_for_enabled_modes(settings: Settings) -> None:
    memory = build(settings, "caller://acme")
    assert memory is not None and memory.session.tenant == "acme"
    assert memory.attach(profile()) is not None


def test_memory_is_disabled_without_the_flag_or_for_unsafe_runs(settings: Settings) -> None:
    assert build(settings.model_copy(update={"borges_memory": False}), None) is None
    assert build(settings, None, curated=False) is None
    keyless = settings.model_copy(update={"borges_memory_key": None})
    assert build(keyless, "caller://acme") is None
    anonymous = build(keyless, None)
    assert anonymous is not None and anonymous.session.tenant == "public-demo"


def test_reads_can_be_off(settings: Settings) -> None:
    memory = build(settings, "caller://acme", reads=False)
    memory.attach(profile())
    assert memory.session.pool(MemoryKind.VERDICT) == []
