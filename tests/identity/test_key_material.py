from __future__ import annotations

from pathlib import Path

import pytest

from borges.config import Settings
from borges.identity.key_material import (
    ANCHOR_KEY_FILE,
    MEMORY_KEY_FILE,
    ensure_anchor_key,
    ensure_keys,
    ensure_memory_key,
)
from borges.identity.store_key import KEY_FILE_RELATIVE, ensure_store_key
from borges.telemetry.audit_anchor import anchor_path_for
from borges.telemetry.run_telemetry import global_audit_path


def make(tmp_path: Path, **fields) -> Settings:
    return Settings(_env_file=None, borges_home=tmp_path / "home", **fields)


def test_autogen_creates_all_three_keys_owner_only_and_reuses_them(tmp_path: Path) -> None:
    settings = make(tmp_path, borges_store_key_autogen=True, borges_memory=True)
    assert ensure_keys(settings) == {"store": True, "anchor": True, "memory": True}
    home = tmp_path / "home"
    first = {
        p: (home / p).read_text() for p in (KEY_FILE_RELATIVE, ANCHOR_KEY_FILE, MEMORY_KEY_FILE)
    }
    assert len(set(first.values())) == 3
    for relative in first:
        assert (home / relative).stat().st_mode & 0o777 == 0o600
    ensure_keys(settings)
    assert first == {p: (home / p).read_text() for p in first}


def test_reading_an_existing_key_file_needs_no_autogen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ensure_keys(make(tmp_path, borges_store_key_autogen=True, borges_memory=True))
    for name in ("BORGES_STORE_KEY", "BORGES_AUDIT_ANCHOR_KEY", "BORGES_MEMORY_KEY"):
        monkeypatch.delenv(name, raising=False)
    reader = make(tmp_path, borges_memory=True)
    assert ensure_store_key(reader) == (tmp_path / "home" / KEY_FILE_RELATIVE).read_text()
    assert ensure_memory_key(reader) == (tmp_path / "home" / MEMORY_KEY_FILE).read_text()


def test_without_autogen_nothing_is_created(tmp_path: Path) -> None:
    assert ensure_keys(make(tmp_path, borges_memory=True)) == {
        "store": False,
        "anchor": False,
        "memory": False,
    }
    assert not (tmp_path / "home").exists()


def test_the_memory_key_is_only_made_when_memory_is_on(tmp_path: Path) -> None:
    settings = make(tmp_path, borges_store_key_autogen=True)
    assert ensure_keys(settings)["memory"] is False
    assert not (tmp_path / "home" / MEMORY_KEY_FILE).exists()


def test_an_existing_unsigned_anchor_blocks_a_new_anchor_key(tmp_path: Path) -> None:
    settings = make(tmp_path, borges_store_key_autogen=True)
    anchors = anchor_path_for(global_audit_path(settings))
    anchors.parent.mkdir(parents=True)
    anchors.write_text("{}\n")
    assert ensure_anchor_key(settings, True) is None


def test_a_legacy_unkeyed_home_gets_no_anchor_key(tmp_path: Path) -> None:
    settings = make(tmp_path, borges_store_key_autogen=True)
    legacy = tmp_path / "home" / "identity" / "keys.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("")
    assert ensure_keys(settings)["store"] is False
    assert not (tmp_path / "home" / ANCHOR_KEY_FILE).exists()
