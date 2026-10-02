from __future__ import annotations

import os
from pathlib import Path

import pytest

from borges.config import Settings
from borges.identity.store_key import (
    KEY_FILE_RELATIVE,
    UNKEYED_NOTICE,
    derive_key,
    ensure_store_key,
    store_key,
)


def make(tmp_path: Path, **kwargs: object) -> Settings:
    return Settings(_env_file=None, borges_home=tmp_path / "home", **kwargs)


def test_store_key_prefers_the_store_key_then_the_anchor_key(tmp_path: Path) -> None:
    assert store_key(make(tmp_path)) is None
    assert store_key(make(tmp_path, borges_audit_anchor_key="a")) == "a"
    both = make(tmp_path, borges_audit_anchor_key="a", borges_store_key="s")
    assert store_key(both) == "s"


def test_derived_keys_differ_by_domain_and_purpose() -> None:
    values = {derive_key("k", d, p) for d in ("x", "y") for p in ("chain", "anchor")}
    assert len(values) == 4
    assert derive_key("k", "x", "chain") == derive_key("k", "x", "chain")


def test_autogen_creates_a_private_key_file_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BORGES_STORE_KEY", "placeholder")
    monkeypatch.delenv("BORGES_STORE_KEY")
    settings = make(tmp_path, borges_store_key_autogen=True)
    first = ensure_store_key(settings)
    path = settings.borges_home / KEY_FILE_RELATIVE
    assert first and len(first) == 64 and (path.stat().st_mode & 0o777) == 0o600
    monkeypatch.delenv("BORGES_STORE_KEY")
    assert ensure_store_key(settings) == first
    assert os.environ["BORGES_STORE_KEY"] == first


def test_without_autogen_or_key_nothing_is_created(tmp_path: Path) -> None:
    settings = make(tmp_path)
    assert ensure_store_key(settings) is None
    assert not (settings.borges_home / KEY_FILE_RELATIVE).exists()
    assert "accidental edits" in UNKEYED_NOTICE


def test_autogen_leaves_existing_unkeyed_stores_unkeyed(tmp_path: Path) -> None:
    settings = make(tmp_path, borges_store_key_autogen=True)
    keys = settings.borges_home / "identity" / "keys.jsonl"
    keys.parent.mkdir(parents=True)
    keys.write_text("")
    assert ensure_store_key(settings) is None
    assert not (settings.borges_home / KEY_FILE_RELATIVE).exists()
