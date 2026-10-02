from __future__ import annotations

from typing import Any

from borges.fleet.versions import format_version, parse_version

FIRST_VERSION = "1.0.0"
MAJOR_FIELDS = ("capabilities", "principal", "kind", "role")
MINOR_FIELDS = ("prompt_sha", "output_schema_sha", "code_sha", "model_id")
CHANGELOG_FIELDS = (
    *MAJOR_FIELDS,
    *MINOR_FIELDS,
    "purpose",
    "display_name",
    "lifecycle",
    "owner",
    "department",
)


def changed_fields(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    return [name for name in CHANGELOG_FIELDS if previous.get(name) != current.get(name)]


def bump_kind(changed: list[str]) -> str:
    if any(name in MAJOR_FIELDS for name in changed):
        return "major"
    if any(name in MINOR_FIELDS for name in changed):
        return "minor"
    return "patch"


def next_version(latest: str | None, kind: str) -> str:
    if latest is None:
        return FIRST_VERSION
    major, minor, patch = parse_version(latest)
    if kind == "major":
        return format_version((major + 1, 0, 0))
    if kind == "minor":
        return format_version((major, minor + 1, 0))
    return format_version((major, minor, patch + 1))


def _short(value: Any) -> str:
    text = str(value)
    return text[:8] if len(text) == 64 else text


def changelog_line(changed: list[str], previous: dict[str, Any], current: dict[str, Any]) -> str:
    if not previous:
        return "initial definition"
    parts = []
    for name in changed:
        if name == "capabilities":
            old, new = set(previous.get(name) or []), set(current.get(name) or [])
            added = ", ".join(f"+{c}" for c in sorted(new - old))
            removed = ", ".join(f"-{c}" for c in sorted(old - new))
            parts.append("capabilities " + " ".join(x for x in (added, removed) if x))
        else:
            parts.append(f"{name} {_short(previous.get(name))} -> {_short(current.get(name))}")
    return "; ".join(parts) if parts else "definition changed"
