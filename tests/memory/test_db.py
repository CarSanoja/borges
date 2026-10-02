from __future__ import annotations

from pathlib import Path

from borges.config import Settings
from borges.memory.db import db_path, open_memory_db
from borges.memory.kinds import MemoryKind


def test_one_table_per_kind_in_wal_mode(tmp_path: Path) -> None:
    conn = open_memory_db(tmp_path / "deep" / "m.db")
    names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {kind.table for kind in MemoryKind} <= names
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_reopening_keeps_the_rows(tmp_path: Path) -> None:
    path = tmp_path / "m.db"
    conn = open_memory_db(path)
    conn.execute(
        "INSERT INTO memory_note (tenant, dataset_fp, family_fp, signature, run_id, created_at,"
        " last_used_at, expires_at, size, payload) VALUES ('t','d','f','s','r',1,1,2,1,x'00')"
    )
    conn.commit()
    conn.close()
    assert open_memory_db(path).execute("SELECT COUNT(*) FROM memory_note").fetchone()[0] == 1


def test_path_lives_under_the_home(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, borges_home=tmp_path)
    assert db_path(settings) == tmp_path / "memory" / "memory.db"
