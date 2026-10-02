from __future__ import annotations

import logging
import time
from collections import Counter
from typing import Any

from borges.armor.report import ArmorReport
from borges.config import Settings
from borges.fleet.models import AgentUse, RunAgents
from borges.memory import audit
from borges.memory.approvals import ApprovalCheck
from borges.memory.entry import MemoryEntry
from borges.memory.kinds import MemoryKind, policy_for
from borges.memory.recalled import Match, Recalled
from borges.memory.repository import MemoryRepository
from borges.memory.screening import screen_payload
from borges.memory.signatures import dataset_fingerprint, family_fingerprint
from borges.memory.similarity import best_match
from borges.memory.tenant import MemoryMode

log = logging.getLogger("borges.memory")
FAMILY_KINDS = (MemoryKind.VERDICT, MemoryKind.ADVERSARY)


class MemorySession:
    """One run's view of the memory bank: reads once per kind, writes once at the end."""

    def __init__(
        self,
        repo: MemoryRepository,
        mode: MemoryMode,
        settings: Settings,
        principal: str | None,
        run_id: str,
        agents: RunAgents | None,
        armor: ArmorReport,
        approvals: ApprovalCheck | None = None,
        reads: bool = True,
    ) -> None:
        assert mode.tenant is not None
        self.repo = repo
        self.mode = mode
        self.tenant: str = mode.tenant
        self.settings = settings
        self.principal = principal
        self.run_id = run_id
        self.agents = agents
        self.armor = armor
        self.approvals = approvals or ApprovalCheck(settings)
        self.reads = reads
        self.dataset_fp = ""
        self.family_fp = ""
        self._pools: dict[MemoryKind, list[MemoryEntry]] = {}
        self._staged: dict[tuple[MemoryKind, str], MemoryEntry] = {}
        self._used: dict[tuple[MemoryKind, int], MemoryEntry] = {}
        self._reused: Counter[str] = Counter()
        self._sources: Counter[str] = Counter()
        self._stored: Counter[str] = Counter()
        self.dropped = 0

    def attach(self, profile) -> str:
        self.dataset_fp = dataset_fingerprint(profile)
        self.family_fp = family_fingerprint(profile)
        return self.dataset_fp

    def _load(self, kind: MemoryKind) -> list[MemoryEntry]:
        family = self.family_fp if kind in FAMILY_KINDS else None
        try:
            loaded = self.repo.load(self.tenant, kind, self.dataset_fp, family)
        except Exception:
            log.warning("memory read failed", exc_info=True)
            return []
        usable: list[MemoryEntry] = []
        for entry in loaded.entries:
            if entry.run_id == self.run_id:
                continue
            if not self.approvals.approved(entry.agent_id, entry.definition_sha):
                self.dropped += 1
                continue
            field = f"memory:{kind.value}:{entry.signature[:8]}"
            screened = screen_payload(kind, entry.payload, self.armor, field)
            if screened is None:
                self.dropped += 1
                continue
            entry.payload = screened
            usable.append(entry)
        self.dropped += loaded.unreadable
        audit.record_read(
            self.settings,
            self.principal,
            self.tenant,
            kind.value,
            self.dataset_fp,
            len(loaded.entries) + loaded.unreadable,
            len(usable),
        )
        return usable

    def pool(self, kind: MemoryKind) -> list[MemoryEntry]:
        if not self.reads or not self.dataset_fp:
            return []
        if kind not in self._pools:
            self._pools[kind] = self._load(kind)
        return self._pools[kind]

    def find(self, kind: MemoryKind, signature: str) -> Recalled | None:
        found = [e for e in self.pool(kind) if e.signature == signature]
        if not found:
            return None
        found.sort(key=lambda e: e.dataset_fp != self.dataset_fp)
        match: Match = "exact" if found[0].dataset_fp == self.dataset_fp else "family"
        return Recalled(found[0], match)

    def similar(self, kind: MemoryKind, context: str, text: str) -> Recalled | None:
        pool = [e for e in self.pool(kind) if e.payload.get("ctx") == context]
        hit = best_match(text, (e.text for e in pool), self.settings.borges_memory_similarity)
        if hit is None:
            return None
        return Recalled(pool[hit.index], "similar", hit.score)

    def used(self, kind: MemoryKind, recalled: Recalled) -> None:
        entry = recalled.entry
        if entry.row_id is not None and (kind, entry.row_id) not in self._used:
            self._used[(kind, entry.row_id)] = entry
            self._reused[kind.value] += 1
            self._sources[entry.run_id] += 1

    def _agent_use(self, kind: MemoryKind) -> AgentUse | None:
        agent_id = policy_for(kind).agent_id
        if agent_id is None or self.agents is None:
            return None
        use = next((a for a in self.agents.agents if a.agent_id == agent_id), None)
        return use if use is not None and use.approval == "approved" else None

    def stage(self, kind: MemoryKind, signature: str, payload: dict[str, Any]) -> bool:
        if not self.dataset_fp:
            return False
        use = self._agent_use(kind)
        if policy_for(kind).agent_id is not None and use is None:
            return False
        screened = screen_payload(kind, payload, self.armor, f"memory:write:{kind.value}")
        if screened is None:
            return False
        self._staged[(kind, signature)] = MemoryEntry(
            kind=kind,
            dataset_fp=self.dataset_fp,
            family_fp=self.family_fp,
            signature=signature,
            payload=screened,
            run_id=self.run_id,
            agent_id=use.agent_id if use else None,
            agent_version=use.version if use else None,
            definition_sha=use.definition_sha if use else None,
            created_at=time.time(),
        )
        return True

    def flush(self) -> None:
        for kind in MemoryKind:
            rows = [e for (k, _), e in self._staged.items() if k is kind]
            stored = 0
            for entry in rows:
                try:
                    stored += int(self.repo.put(self.tenant, entry))
                except Exception:
                    log.warning("memory write failed", exc_info=True)
            if stored:
                self._stored[kind.value] += stored
                audit.record_write(
                    self.settings, self.principal, self.tenant, kind.value, self.dataset_fp, stored
                )
        self._staged.clear()
        for kind in MemoryKind:
            ids = [i for (k, i) in self._used if k is kind]
            if ids:
                try:
                    self.repo.touch(self.tenant, kind, ids)
                except Exception:
                    log.warning("memory touch failed", exc_info=True)
        self._used.clear()

    def usage(self) -> dict[str, Any]:
        return {
            "mode": self.mode.label,
            "encrypted": self.mode.encrypted,
            "dataset": self.dataset_fp[:12],
            "reused": dict(self._reused),
            "stored": dict(self._stored),
            "sources": [{"run_id": r, "count": n} for r, n in sorted(self._sources.items())],
            "dropped": self.dropped,
        }
