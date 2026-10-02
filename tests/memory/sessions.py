from __future__ import annotations

from borges.armor.report import ArmorReport
from borges.config import Settings
from borges.fleet.provenance import run_provenance
from borges.memory.db import db_path, open_memory_db
from borges.memory.repository import MemoryRepository
from borges.memory.run_memory import RunMemory
from borges.memory.seal import Sealer
from borges.memory.session import MemorySession
from borges.memory.tenant import resolve_mode
from tests.memory.plans import profile


def make_session(
    settings: Settings,
    run_id: str = "r_new",
    principal: str | None = "caller://acme",
    reads: bool = True,
    armor: ArmorReport | None = None,
) -> MemorySession:
    repo = MemoryRepository(open_memory_db(db_path(settings)), Sealer(settings.borges_memory_key))
    mode = resolve_mode(settings, principal)
    return MemorySession(
        repo,
        mode,
        settings,
        principal,
        run_id,
        run_provenance(settings, "scripted"),
        armor if armor is not None else ArmorReport(),
        reads=reads,
    )


def make_memory(settings: Settings, **kwargs) -> RunMemory:
    memory = RunMemory(make_session(settings, **kwargs))
    memory.attach(profile())
    return memory
