from __future__ import annotations

from borges.fleet.semver import bump_kind, changed_fields, changelog_line, next_version


def test_first_version() -> None:
    assert next_version(None, "major") == "1.0.0"


def test_bumps() -> None:
    assert next_version("1.2.3", "major") == "2.0.0"
    assert next_version("1.2.3", "minor") == "1.3.0"
    assert next_version("1.2.3", "patch") == "1.2.4"


def test_capabilities_are_major_and_prompt_is_minor() -> None:
    assert bump_kind(["prompt_sha", "capabilities"]) == "major"
    assert bump_kind(["prompt_sha"]) == "minor"
    assert bump_kind(["output_schema_sha"]) == "minor"
    assert bump_kind(["purpose"]) == "patch"


def test_changelog_names_what_changed() -> None:
    old = {"capabilities": ["a"], "prompt_sha": "x" * 64}
    new = {"capabilities": ["a", "b"], "prompt_sha": "y" * 64}
    changed = changed_fields(old, new)
    line = changelog_line(changed, old, new)
    assert "capabilities +b" in line and "prompt_sha xxxxxxxx -> yyyyyyyy" in line
    assert changelog_line([], {}, new) == "initial definition"
