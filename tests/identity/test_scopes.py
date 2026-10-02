from __future__ import annotations

import pytest

from borges.identity.scopes import KNOWN_SCOPES, PUBLIC_SCOPES, UnknownScope, parse_scopes


def test_public_scopes_are_exactly_the_demo_path() -> None:
    assert {
        "cases:read",
        "runs:read",
        "runs:create:scripted",
        "runs:create:live:curated",
        "recordings:read",
        "memory:read",
    } == PUBLIC_SCOPES


def test_parse_scopes_trims_and_dedupes() -> None:
    assert parse_scopes(" uploads:write, audit:read ,uploads:write") == {
        "uploads:write",
        "audit:read",
    }


def test_unknown_scope_is_rejected_with_the_known_list() -> None:
    with pytest.raises(UnknownScope, match="nope"):
        parse_scopes("audit:read,nope")


def test_empty_scopes_are_rejected() -> None:
    with pytest.raises(UnknownScope):
        parse_scopes(" , ")


def test_named_scopes_exist() -> None:
    for scope in ("uploads:write", "runs:create:live:upload", "registry:publish", "admin"):
        assert scope in KNOWN_SCOPES


def test_memory_write_is_named_only() -> None:
    from borges.identity.scopes import MEMORY_WRITE, NAMED_ONLY_SCOPES

    assert MEMORY_WRITE in NAMED_ONLY_SCOPES and MEMORY_WRITE not in PUBLIC_SCOPES
