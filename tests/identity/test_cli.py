from __future__ import annotations

import pytest
from typer.testing import CliRunner

from borges.cli import app
from borges.config import Settings
from borges.identity.keystore import KeyStore
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import global_audit_path

runner = CliRunner()


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("BORGES_HOME", str(tmp_path / "home"))
    return Settings(_env_file=None, borges_home=tmp_path / "home")


def test_create_prints_the_secret_once_and_list_never_does(home: Settings) -> None:
    created = runner.invoke(
        app,
        [
            "keys",
            "create",
            "--name",
            "ci",
            "--scopes",
            "audit:read,uploads:write",
            "--expires",
            "30d",
        ],
    )
    assert created.exit_code == 0, created.output
    token = next(line for line in created.output.splitlines() if line.startswith("bk_"))
    listed = runner.invoke(app, ["keys", "list"])
    assert listed.exit_code == 0
    assert token not in listed.output and token.split("_", 2)[2] not in listed.output
    assert "ci\tactive\taudit:read,uploads:write" in listed.output
    store = KeyStore(home.borges_home / "identity" / "keys.jsonl")
    assert store.authenticate(token)[0] is not None


def test_revoke_stops_the_key_and_is_audited(home: Settings) -> None:
    created = runner.invoke(app, ["keys", "create", "--name", "ci", "--scopes", "audit:read"])
    key_id = next(
        line for line in created.output.splitlines() if line.startswith("key_id")
    ).split()[1]
    token = next(line for line in created.output.splitlines() if line.startswith("bk_"))
    assert runner.invoke(app, ["keys", "revoke", key_id]).exit_code == 0
    store = KeyStore(home.borges_home / "identity" / "keys.jsonl")
    assert store.authenticate(token)[1] == "revoked"
    kinds = [r.kind for r in read_records(global_audit_path(home))]
    assert kinds == ["identity.key.created", "identity.key.revoked"]
    assert "revoked" in runner.invoke(app, ["keys", "list"]).output


def test_bad_scope_name_and_unknown_key_are_errors() -> None:
    assert runner.invoke(app, ["keys", "create", "--name", "ci", "--scopes", "root"]).exit_code == 2
    assert (
        runner.invoke(app, ["keys", "create", "--name", "A B", "--scopes", "admin"]).exit_code == 2
    )
    assert runner.invoke(app, ["keys", "revoke", "nope"]).exit_code == 2


def test_verify_detects_tampering(home: Settings) -> None:
    runner.invoke(app, ["keys", "create", "--name", "ci", "--scopes", "audit:read"])
    assert runner.invoke(app, ["keys", "verify"]).exit_code == 0
    path = home.borges_home / "identity" / "keys.jsonl"
    path.write_text(path.read_text().replace("audit:read", "admin"))
    result = runner.invoke(app, ["keys", "verify"])
    assert result.exit_code == 1 and "BROKEN" in result.output
    assert runner.invoke(app, ["keys", "list"]).exit_code == 1


def test_empty_list() -> None:
    assert "no keys" in runner.invoke(app, ["keys", "list"]).output


def test_verify_states_the_mode_and_detects_truncation(
    home: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("a", "b"):
        runner.invoke(app, ["keys", "create", "--name", name, "--scopes", "audit:read"])
    plain = runner.invoke(app, ["keys", "verify"])
    assert "unkeyed: tamper-evident only against accidental edits" in plain.output
    path = home.borges_home / "identity" / "keys.jsonl"
    path.write_text(path.read_text().splitlines()[0] + "\n")
    cut = runner.invoke(app, ["keys", "verify"])
    assert cut.exit_code == 1 and "truncated" in cut.output
    assert "accidental edits" in cut.output


def test_verify_with_a_store_key_says_keyed(
    home: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BORGES_STORE_KEY", "k")
    runner.invoke(app, ["keys", "create", "--name", "a", "--scopes", "audit:read"])
    result = runner.invoke(app, ["keys", "verify"])
    assert result.exit_code == 0 and "keyed: HMAC-SHA256" in result.output
    assert "accidental" not in result.output
