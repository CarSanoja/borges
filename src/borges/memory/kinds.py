from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

PUBLIC_TENANT = "public-demo"
DAY_S = 86400.0


class MemoryKind(StrEnum):
    VERDICT = "verdict"
    CODE = "code"
    ADVERSARY = "adversary"
    NOTE = "note"

    @property
    def table(self) -> str:
        return f"memory_{self.value}"


@dataclass(frozen=True)
class KindPolicy:
    ttl_s: float
    max_rows: int
    max_bytes: int
    agent_id: str | None


POLICIES: dict[MemoryKind, KindPolicy] = {
    MemoryKind.VERDICT: KindPolicy(
        ttl_s=90 * DAY_S, max_rows=2000, max_bytes=4_000_000, agent_id="judge"
    ),
    MemoryKind.CODE: KindPolicy(
        ttl_s=30 * DAY_S, max_rows=1000, max_bytes=8_000_000, agent_id="coder"
    ),
    MemoryKind.ADVERSARY: KindPolicy(
        ttl_s=60 * DAY_S, max_rows=500, max_bytes=2_000_000, agent_id="adversary"
    ),
    MemoryKind.NOTE: KindPolicy(ttl_s=3650 * DAY_S, max_rows=200, max_bytes=500_000, agent_id=None),
}


def policy_for(kind: MemoryKind) -> KindPolicy:
    return POLICIES[kind]


MAX_PAYLOAD_BYTES = 64_000
