from __future__ import annotations

from pathlib import Path

import pytest

from borges.config import Settings
from borges.runtime.db import RuntimeDb, open_runtime_db, runtime_db_path


def test_database_uses_wal_and_creates_its_tables(tmp_path: Path) -> None:
    db = RuntimeDb(tmp_path / "a" / "runtime.db")
    with db.connect() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert mode == "wal"
    assert {"jobs", "idempotency", "dead_letter", "checkpoints", "schedules"} <= tables


def test_path_lives_under_borges_home(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, borges_home=tmp_path)
    assert runtime_db_path(settings) == tmp_path / "runtime" / "runtime.db"
    assert open_runtime_db(settings).path.is_file()


def test_transaction_rolls_back_on_error(db: RuntimeDb) -> None:
    with pytest.raises(RuntimeError), db.transaction() as conn:
        conn.execute(
            "INSERT INTO schedules (id, case_id, every_s, principal, next_run, created_at)"
            " VALUES ('s', 'c', 60, 'p', 1, 1)"
        )
        raise RuntimeError("boom")
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM schedules").fetchone()[0] == 0


def test_two_connections_see_committed_rows(db: RuntimeDb) -> None:
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO schedules (id, case_id, every_s, principal, next_run, created_at)"
            " VALUES ('s', 'c', 60, 'p', 1, 1)"
        )
    other = RuntimeDb(db.path)
    with other.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM schedules").fetchone()[0] == 1
