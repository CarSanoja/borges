from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.config import REPO_ROOT, Settings
from borges.gateway.errors import PolicyError
from borges.gateway.policy_load import load_policy, policy_for
from borges.gateway.policy_view import agent_policy_sha, effective_policy

SOURCE = REPO_ROOT / "policy" / "gateway.json"


def copy_policy(tmp_path: Path, mutate=None) -> Path:
    data = json.loads(SOURCE.read_text())
    if mutate:
        mutate(data)
    target = tmp_path / "gateway.json"
    target.write_text(json.dumps(data))
    return target


def test_sha_is_stable_and_ignores_formatting(tmp_path: Path) -> None:
    first = load_policy(copy_policy(tmp_path))
    pretty = tmp_path / "pretty.json"
    pretty.write_text(json.dumps(json.loads(SOURCE.read_text()), indent=4))
    assert load_policy(pretty).sha == first.sha and len(first.sha) == 64


def test_sha_changes_with_any_rule(tmp_path: Path) -> None:
    base = load_policy(copy_policy(tmp_path)).sha
    changed = load_policy(
        copy_policy(tmp_path, lambda d: d["agents"]["judge"].update(max_tokens=1))
    )
    assert changed.sha != base


def test_missing_file_is_a_policy_error(tmp_path: Path) -> None:
    with pytest.raises(PolicyError, match="cannot be read"):
        load_policy(tmp_path / "absent.json")


def test_invalid_json_is_a_policy_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{nope")
    with pytest.raises(PolicyError, match="not valid JSON"):
        load_policy(path)


def test_schema_violation_names_the_field(tmp_path: Path) -> None:
    path = copy_policy(tmp_path, lambda d: d["agents"]["judge"].update(egress="all"))
    with pytest.raises(PolicyError, match="agents.judge.egress"):
        load_policy(path)


def test_settings_point_at_the_tracked_file() -> None:
    loaded = policy_for(Settings(_env_file=None))
    assert loaded.path == SOURCE and loaded.agent("planner") is not None
    assert loaded.agent("harness") is None


def test_effective_policy_has_sha_and_no_secret_fields() -> None:
    document = effective_policy(Settings(_env_file=None))
    dumped = json.dumps(document.model_dump(mode="json")).lower()
    assert document.sha == policy_for(Settings(_env_file=None)).sha
    assert "api_key" not in dumped and "secret" not in dumped and "password" not in dumped
    assert "bearer" not in dumped


def test_agent_policy_sha_per_agent_and_component() -> None:
    settings = Settings(_env_file=None)
    judge = agent_policy_sha(settings, "judge")
    assert judge and judge != agent_policy_sha(settings, "planner")
    assert agent_policy_sha(settings, "code_guard") is None
    assert agent_policy_sha(settings, "harness", sandbox=True)
