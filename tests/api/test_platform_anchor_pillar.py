from __future__ import annotations

from pathlib import Path

import pytest

from borges.api import platform_audit, platform_guard
from borges.config import Settings
from borges.identity.key_material import ensure_keys
from borges.telemetry.run_telemetry import global_audit_log


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("BORGES_AUDIT_ANCHOR_KEY", "BORGES_STORE_KEY"):
        monkeypatch.delenv(name, raising=False)
    platform_audit._CACHE.clear()


def make(tmp_path: Path, **fields) -> Settings:
    return Settings(
        _env_file=None, borges_home=tmp_path / "home", borges_audit_anchor_every=1, **fields
    )


def write_records(settings: Settings, count: int = 2) -> None:
    log = global_audit_log(settings)
    for index in range(count):
        log.append("test.kind", principal="tester", reason=f"r{index}")


def test_an_unsigned_anchor_makes_the_pillar_warn_with_a_reason(tmp_path: Path) -> None:
    settings = make(tmp_path)
    write_records(settings)
    pillar = platform_guard.observability(settings)
    assert pillar["status"] == "attention"
    assert "unsigned" in pillar["summary"] and "BORGES_AUDIT_ANCHOR_KEY" in pillar["summary"]
    assert pillar["facts"]["audit_chain"]["signed_anchor"] is False


def test_a_signed_anchor_keeps_the_pillar_ok(tmp_path: Path) -> None:
    settings = make(tmp_path, borges_audit_anchor_key="k" * 32)
    write_records(settings)
    pillar = platform_guard.observability(settings)
    assert pillar["status"] == "ok"
    assert pillar["facts"]["audit_chain"]["signed_anchor"] is True


def test_a_fresh_autogen_serve_signs_its_anchors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make(tmp_path, borges_store_key_autogen=True)
    ensure_keys(settings)
    fresh = make(tmp_path, borges_store_key_autogen=True)
    assert fresh.borges_audit_anchor_key
    write_records(fresh)
    pillar = platform_guard.observability(fresh)
    assert pillar["status"] == "ok"
    assert pillar["facts"]["audit_chain"]["signed_anchor"] is True
    monkeypatch.delenv("BORGES_AUDIT_ANCHOR_KEY")
    monkeypatch.delenv("BORGES_STORE_KEY")


def test_the_gateway_states_how_sandbox_network_is_really_enforced(tmp_path: Path) -> None:
    facts = platform_guard.gateway(make(tmp_path))["facts"]
    assert facts["sandbox_network"] == "none"
    note = facts["sandbox_network_enforcement"]
    assert note.startswith("declared; enforced in-process")
    assert "ConTree's own egress is not configured by Borges" in note
