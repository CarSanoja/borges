from __future__ import annotations

import fcntl
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from borges.llm.cache import atomic_write_text
from borges.llm.client import BudgetExceeded

_PROCESS_LOCK = threading.RLock()
_RESERVED: dict[Path, float] = {}


class RunBudget:
    """Per-run cap. Reservations hold the estimate of in-flight calls until they settle."""

    def __init__(self, cap_usd: float) -> None:
        self.cap_usd = cap_usd
        self._total = 0.0
        self._reserved = 0.0

    @property
    def total(self) -> float:
        return self._total

    def _check(self, estimate_usd: float) -> None:
        if self._total + self._reserved + estimate_usd > self.cap_usd:
            raise BudgetExceeded(
                f"run budget ${self.cap_usd:.4f} would be exceeded "
                f"(spent ${self._total:.4f}, next call ~${estimate_usd:.4f})"
            )

    async def ensure_room(self, estimate_usd: float) -> None:
        self._check(estimate_usd)

    async def reserve(self, estimate_usd: float) -> None:
        self._check(estimate_usd)
        self._reserved += estimate_usd

    async def release(self, estimate_usd: float) -> None:
        self._reserved = max(0.0, self._reserved - estimate_usd)

    async def settle(self, estimate_usd: float, cost_usd: float) -> None:
        await self.release(estimate_usd)
        self._total += cost_usd

    async def record(self, cost_usd: float) -> None:
        self._total += cost_usd


class SpendLedger:
    """Persistent spend total shared by every run and process, with a hard cap.

    Calls reserve their estimated cost before the request and settle with the actual cost
    afterwards. Read-modify-write cycles are serialised across instances and processes.
    """

    def __init__(self, path: Path, cap_usd: float) -> None:
        self.path = path
        self.cap_usd = cap_usd
        self._key = path.resolve()

    @contextmanager
    def _exclusive(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _PROCESS_LOCK, self.path.with_suffix(".lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def _read(self) -> dict[str, object]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {"total_usd": 0.0, "calls": 0, "updated_at": None}
        return data if isinstance(data, dict) else {"total_usd": 0.0, "calls": 0}

    @property
    def total(self) -> float:
        return float(self._read().get("total_usd", 0.0))  # type: ignore[arg-type]

    def _check(self, estimate_usd: float) -> None:
        total = self.total
        reserved = _RESERVED.get(self._key, 0.0)
        if total + reserved + estimate_usd > self.cap_usd:
            raise BudgetExceeded(
                f"spend cap ${self.cap_usd:.2f} would be exceeded "
                f"(spent ${total:.4f}, next call ~${estimate_usd:.4f})"
            )

    async def ensure_room(self, estimate_usd: float) -> None:
        with self._exclusive():
            self._check(estimate_usd)

    async def reserve(self, estimate_usd: float) -> None:
        with self._exclusive():
            self._check(estimate_usd)
            _RESERVED[self._key] = _RESERVED.get(self._key, 0.0) + estimate_usd

    async def release(self, estimate_usd: float) -> None:
        with self._exclusive():
            _RESERVED[self._key] = max(0.0, _RESERVED.get(self._key, 0.0) - estimate_usd)

    async def settle(self, estimate_usd: float, cost_usd: float) -> None:
        with self._exclusive():
            _RESERVED[self._key] = max(0.0, _RESERVED.get(self._key, 0.0) - estimate_usd)
            self._add(cost_usd)

    async def record(self, cost_usd: float) -> None:
        with self._exclusive():
            self._add(cost_usd)

    def _add(self, cost_usd: float) -> None:
        data = self._read()
        payload = {
            "total_usd": float(data.get("total_usd", 0.0)) + cost_usd,  # type: ignore[arg-type]
            "calls": int(data.get("calls", 0)) + 1,  # type: ignore[call-overload]
            "updated_at": datetime.now(UTC).isoformat(),
        }
        atomic_write_text(self.path, json.dumps(payload))
