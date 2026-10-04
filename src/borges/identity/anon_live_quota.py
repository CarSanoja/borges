from __future__ import annotations

import hashlib
import hmac
import sqlite3
import time
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from borges.config import Settings
from borges.identity.store_key import read_key_file, write_key_file

DAY_S = 86400.0
HOUR_S = 3600.0
DB_NAME = "anon_live_quota.sqlite"
SALT_FILE = Path("identity") / "ip.salt"
SCHEMA = (
    "CREATE TABLE IF NOT EXISTS anon_live ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, ip_hash TEXT NOT NULL, ts REAL NOT NULL)",
    "CREATE INDEX IF NOT EXISTS anon_live_ip ON anon_live (ip_hash, ts)",
    "CREATE INDEX IF NOT EXISTS anon_live_ts ON anon_live (ts)",
)


@dataclass(frozen=True)
class QuotaView:
    per_client_per_day: int
    remaining: int
    resets_at: float | None
    global_per_hour: int
    global_remaining: int
    est_cost_per_run_usd: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "per_client_per_day": self.per_client_per_day,
            "remaining": self.remaining,
            "resets_at": _iso(self.resets_at),
            "global_per_hour": self.global_per_hour,
            "global_remaining": self.global_remaining,
            "est_cost_per_run_usd": self.est_cost_per_run_usd,
        }


def _iso(stamp: float | None) -> str | None:
    return None if stamp is None else datetime.fromtimestamp(stamp, UTC).isoformat()


def _exceeded(reason: str, reset_at: float, now: float) -> HTTPException:
    wait = max(1, int(reset_at - now) + 1)
    return HTTPException(
        status_code=429,
        detail=f"Anonymous live-run quota: {reason}; it resets at {_iso(reset_at)}. "
        "Watch the recorded run or use an API key.",
        headers={"Retry-After": str(wait)},
    )


class AnonLiveQuota:
    """Durable per-client and global limits on live runs started without an API key."""

    def __init__(self, settings: Settings, clock: Callable[[], float] = time.time) -> None:
        self._settings = settings
        self._clock = clock
        self._path = Path(settings.borges_home) / DB_NAME
        self._salt: str | None = None

    def client_hash(self, ip: str) -> str:
        if self._salt is None:
            self._salt = self._load_salt()
        return hmac.new(self._salt.encode(), ip.encode(), hashlib.sha256).hexdigest()[:32]

    def _load_salt(self) -> str:
        if self._settings.borges_ip_hash_salt:
            return self._settings.borges_ip_hash_salt
        path = Path(self._settings.borges_home) / SALT_FILE
        existing = read_key_file(path)
        if existing:
            return existing
        try:
            return write_key_file(path)
        except FileExistsError:
            return read_key_file(path) or ""

    def _connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._path, timeout=10, isolation_level=None)
        for statement in SCHEMA:
            conn.execute(statement)
        return conn

    def _counts(
        self, conn: sqlite3.Connection, key: str, now: float
    ) -> tuple[list[float], list[float]]:
        mine = conn.execute(
            "SELECT ts FROM anon_live WHERE ip_hash = ? AND ts > ? ORDER BY ts",
            (key, now - DAY_S),
        ).fetchall()
        hour = conn.execute(
            "SELECT ts FROM anon_live WHERE ts > ? ORDER BY ts", (now - HOUR_S,)
        ).fetchall()
        return [row[0] for row in mine], [row[0] for row in hour]

    def view(self, ip: str) -> QuotaView:
        s, now = self._settings, self._clock()
        with closing(self._connect()) as conn:
            mine, hour = self._counts(conn, self.client_hash(ip), now)
        return QuotaView(
            s.borges_anon_live_per_client_per_day,
            max(0, s.borges_anon_live_per_client_per_day - len(mine)),
            mine[0] + DAY_S if mine else None,
            s.borges_anon_live_global_per_hour,
            max(0, s.borges_anon_live_global_per_hour - len(hour)),
            s.borges_typical_run_cost_usd,
        )

    def check(self, ip: str) -> None:
        s, now, key = self._settings, self._clock(), self.client_hash(ip)
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM anon_live WHERE ts <= ?", (now - DAY_S,))
            mine, hour = self._counts(conn, key, now)
        limit = s.borges_anon_live_per_client_per_day
        if len(mine) >= limit:
            reset = mine[-limit] + DAY_S if limit > 0 else now + DAY_S
            raise _exceeded(f"{limit} live runs per client per 24 hours", reset, now)
        cap = s.borges_anon_live_global_per_hour
        if len(hour) >= cap:
            reset = hour[-cap] + HOUR_S if cap > 0 else now + HOUR_S
            raise _exceeded(f"{cap} anonymous live runs per hour on this server", reset, now)

    def record(self, ip: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO anon_live (ip_hash, ts) VALUES (?, ?)",
                (self.client_hash(ip), self._clock()),
            )
