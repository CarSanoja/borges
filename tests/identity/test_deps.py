from __future__ import annotations

import pytest
from fastapi import HTTPException

from borges.identity.deps import require_scope
from borges.identity.principal import ANONYMOUS, Principal


def test_require_scope_passes_for_held_scope() -> None:
    require_scope(ANONYMOUS, "cases:read")


def test_require_scope_names_the_missing_scope() -> None:
    with pytest.raises(HTTPException) as caught:
        require_scope(ANONYMOUS, "uploads:write")
    assert caught.value.status_code == 403
    assert "uploads:write" in caught.value.detail


def test_any_of_scopes_is_enough() -> None:
    named = Principal(id="caller://a", kind="key", scopes=frozenset({"audit:read"}))
    require_scope(named, "uploads:write", "audit:read")
