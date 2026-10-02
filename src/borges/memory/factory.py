from __future__ import annotations

from borges.armor.report import ArmorReport
from borges.config import Settings
from borges.fleet.models import RunAgents
from borges.memory.db import db_path, open_memory_db
from borges.memory.repository import MemoryRepository
from borges.memory.run_memory import RunMemory
from borges.memory.seal import Sealer
from borges.memory.session import MemorySession
from borges.memory.tenant import resolve_mode


def open_repository(settings: Settings) -> MemoryRepository:
    return MemoryRepository(open_memory_db(db_path(settings)), Sealer(settings.borges_memory_key))


def build_run_memory(
    settings: Settings,
    principal_id: str | None,
    run_id: str,
    agents: RunAgents | None,
    armor: ArmorReport,
    curated_as_is: bool,
    reads: bool = True,
) -> RunMemory | None:
    mode = resolve_mode(settings, principal_id, curated_as_is)
    if not mode.enabled:
        return None
    session = MemorySession(
        open_repository(settings), mode, settings, principal_id, run_id, agents, armor, reads=reads
    )
    return RunMemory(session)
