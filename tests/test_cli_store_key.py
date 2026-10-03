from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from borges import cli
from borges.config import get_settings
from borges.identity.key_material import ANCHOR_KEY_FILE, MEMORY_KEY_FILE
from borges.identity.store_key import KEY_FILE_RELATIVE
from tests.identity.keys import make_key

runner = CliRunner()
KEY_VARS = ("BORGES_STORE_KEY", "BORGES_AUDIT_ANCHOR_KEY", "BORGES_MEMORY_KEY")


PLATFORM: list[dict] = []


def forget_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in KEY_VARS:
        monkeypatch.setenv(name, "x")
        monkeypatch.delenv(name)


@pytest.fixture
def served_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    monkeypatch.setenv("BORGES_HOME", str(home))
    monkeypatch.setenv("BORGES_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("BORGES_STORE_KEY_AUTOGEN", "true")
    monkeypatch.setenv("BORGES_MEMORY", "true")
    monkeypatch.setenv("BORGES_REGISTRY_ENFORCE", "true")

    def fake_run(app, **_: object) -> None:
        with TestClient(app) as client:
            assert client.get("/api/agents").status_code == 200
            platform = client.get("/api/platform")
            assert platform.status_code == 200
            PLATFORM.append({p["id"]: p for p in platform.json()["pillars"]})
            assert client.get("/api/audit").status_code == 403

    monkeypatch.setattr("uvicorn.run", fake_run)
    assert runner.invoke(cli.app, ["serve"]).exit_code == 0
    return home


def test_serve_generates_store_anchor_and_memory_keys_with_mode_0600(served_home: Path) -> None:
    for relative in (KEY_FILE_RELATIVE, ANCHOR_KEY_FILE, MEMORY_KEY_FILE):
        path = served_home / relative
        assert path.is_file() and path.stat().st_mode & 0o777 == 0o600


def test_agents_verify_passes_after_serve_in_a_fresh_process(
    served_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forget_keys(monkeypatch)
    monkeypatch.delenv("BORGES_STORE_KEY_AUTOGEN")
    result = runner.invoke(cli.app, ["agents", "verify"])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("OK") and "keyed" in result.output
    assert result.exception is None
    audit = runner.invoke(cli.app, ["audit", "verify", "global"])
    assert audit.exit_code == 0, audit.output
    keys = runner.invoke(cli.app, ["keys", "verify"])
    assert keys.exit_code == 0, keys.output


def test_a_keyed_store_without_its_key_says_so_instead_of_broken(
    served_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forget_keys(monkeypatch)
    monkeypatch.delenv("BORGES_STORE_KEY_AUTOGEN")
    for relative in (KEY_FILE_RELATIVE, ANCHOR_KEY_FILE):
        (served_home / relative).unlink()
    for command in (["agents", "verify"], ["audit", "verify", "global"]):
        result = runner.invoke(cli.app, command)
        assert result.exit_code == 1
        assert "keyed store, key not available" in result.output
        assert "BROKEN" not in result.output


def test_a_genuinely_tampered_unkeyed_store_still_reads_broken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BORGES_HOME", str(tmp_path / "home"))
    make_key(get_settings(), "runs:read", "someone")
    path = tmp_path / "home" / "identity" / "keys.jsonl"
    path.write_text(path.read_text().replace("someone", "intruder"))
    result = runner.invoke(cli.app, ["keys", "verify"])
    assert result.exit_code == 1 and "BROKEN" in result.output
    assert "keyed store" not in result.output


def test_a_served_demo_reports_keyed_encrypted_and_anchored(served_home: Path) -> None:
    pillars = PLATFORM[-1]
    assert pillars["memory"]["facts"]["encrypted"] is True
    assert pillars["registry"]["facts"]["chain_keyed"] is True
    assert pillars["identity"]["facts"]["keystore"]["keyed"] is True
    chain = pillars["observability"]["facts"]["audit_chain"]
    assert chain["signed_anchor"] is True
