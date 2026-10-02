from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from borges import cli
from borges.config import Settings
from borges.fleet import locations
from tests.identity.keys import make_key

runner = CliRunner()


@pytest.fixture
def empty_home(settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setattr("borges.fleet.cli.get_settings", lambda: settings)
    monkeypatch.setattr(locations, "SEED_PATH", tmp_path / "empty_seed.jsonl")
    return settings


def test_publish_twice_second_is_a_no_op(empty_home: Settings) -> None:
    first = runner.invoke(cli.app, ["agents", "publish"])
    assert first.exit_code == 0 and first.output.count("published") == 12
    second = runner.invoke(cli.app, ["agents", "publish"])
    assert second.exit_code == 0 and "nothing to publish" in second.output


def test_approve_and_retire(empty_home: Settings) -> None:
    runner.invoke(cli.app, ["agents", "publish"])
    approved = runner.invoke(cli.app, ["agents", "approve", "judge", "1.0.0"])
    assert approved.exit_code == 0 and "approved" in approved.output
    listing = runner.invoke(cli.app, ["agents", "list"])
    assert "judge\tactive\t1.0.0 approved" in listing.output
    retired = runner.invoke(cli.app, ["agents", "retire", "judge", "1.0.0"])
    assert retired.exit_code == 0 and "retired" in retired.output
    again = runner.invoke(cli.app, ["agents", "approve", "judge", "1.0.0"])
    assert again.exit_code == 1


def test_unknown_version_exits_2(empty_home: Settings) -> None:
    result = runner.invoke(cli.app, ["agents", "approve", "judge", "7.0.0"])
    assert result.exit_code == 2


def test_publish_with_approve_flag(empty_home: Settings) -> None:
    result = runner.invoke(cli.app, ["agents", "publish", "--approve"])
    assert result.output.count("approved") == 12


@pytest.fixture
def strict_home(empty_home: Settings, monkeypatch: pytest.MonkeyPatch) -> Settings:
    strict = empty_home.model_copy(update={"borges_registry_four_eyes": True})
    monkeypatch.setattr("borges.fleet.cli.get_settings", lambda: strict)
    return strict


def key_for(settings: Settings, name: str, scopes: str) -> str:
    return make_key(settings, scopes, name)


def test_approve_records_the_principal_given_with_as(empty_home: Settings) -> None:
    runner.invoke(cli.app, ["agents", "publish", "--as", "caller://alice"])
    approved = runner.invoke(
        cli.app, ["agents", "approve", "judge", "1.0.0", "--as", "caller://bob"]
    )
    assert approved.exit_code == 0
    record = locations.open_store(empty_home).get("judge", "1.0.0")
    assert record.published_by == "caller://alice"
    assert record.history[-1].by == "caller://bob"


def test_four_eyes_needs_a_key_with_the_approve_scope(strict_home: Settings) -> None:
    runner.invoke(
        cli.app, ["agents", "publish", "--key", key_for(strict_home, "p", "registry:publish")]
    )
    bare = runner.invoke(cli.app, ["agents", "approve", "judge", "1.0.0", "--as", "caller://bob"])
    assert bare.exit_code == 1 and "registry:approve" in bare.output
    wrong = key_for(strict_home, "pub", "registry:publish")
    refused = runner.invoke(cli.app, ["agents", "approve", "judge", "1.0.0", "--key", wrong])
    assert refused.exit_code == 1 and "does not hold" in refused.output


def test_four_eyes_blocks_self_approval_and_allows_a_second_key(strict_home: Settings) -> None:
    alice = key_for(strict_home, "alice", "registry:publish,registry:approve")
    bob = key_for(strict_home, "bob", "registry:approve")
    runner.invoke(cli.app, ["agents", "publish", "--key", alice])
    own = runner.invoke(cli.app, ["agents", "approve", "judge", "1.0.0", "--key", alice])
    assert own.exit_code == 1 and "four-eyes" in own.output
    other = runner.invoke(cli.app, ["agents", "approve", "judge", "1.0.0", "--key", bob])
    assert other.exit_code == 0
    assert locations.open_store(strict_home).get("judge", "1.0.0").history[-1].by == "caller://bob"


def test_four_eyes_publish_cannot_be_attributed_to_an_invented_principal(
    strict_home: Settings,
) -> None:
    bare = runner.invoke(cli.app, ["agents", "publish", "--as", "caller://ghost"])
    assert bare.exit_code == 1 and "registry:publish" in bare.output
    assert not locations.open_store(strict_home).records()
    listing = runner.invoke(cli.app, ["agents", "list"])
    assert listing.exit_code == 0


def test_as_must_match_the_key_principal(strict_home: Settings) -> None:
    bob = key_for(strict_home, "bob", "registry:approve")
    runner.invoke(
        cli.app, ["agents", "publish", "--key", key_for(strict_home, "p", "registry:publish")]
    )
    result = runner.invoke(
        cli.app, ["agents", "approve", "judge", "1.0.0", "--key", bob, "--as", "caller://eve"]
    )
    assert result.exit_code == 1 and "does not match" in result.output


def test_verify_reports_ok_and_tampering(empty_home: Settings) -> None:
    runner.invoke(cli.app, ["agents", "publish", "--approve"])
    assert runner.invoke(cli.app, ["agents", "verify"]).exit_code == 0
    path = locations.store_path(empty_home)
    path.write_text(path.read_text().replace("initial definition", "forged definition", 1))
    result = runner.invoke(cli.app, ["agents", "verify"])
    assert result.exit_code == 1 and "BROKEN" in result.output
    listing = runner.invoke(cli.app, ["agents", "list"])
    assert listing.exit_code == 1 and "Refusing to use it" in listing.output


def test_verify_the_tracked_seed() -> None:
    assert runner.invoke(cli.app, ["agents", "verify", "--seed"]).exit_code == 0
