from __future__ import annotations

from borges.identity.principal import ANONYMOUS, LEGACY, Principal, caller_principal
from borges.identity.scopes import PUBLIC_SCOPES


def test_anonymous_holds_only_the_public_scopes() -> None:
    assert ANONYMOUS.id == "caller://anonymous"
    assert ANONYMOUS.scopes == PUBLIC_SCOPES
    assert ANONYMOUS.anonymous
    assert not ANONYMOUS.has("uploads:write")


def test_admin_implies_every_scope() -> None:
    admin = Principal(id=caller_principal("root"), kind="key", scopes=frozenset({"admin"}))
    assert admin.has("registry:approve")
    assert admin.has_any(("audit:read",))


def test_legacy_token_maps_to_upload_scopes() -> None:
    assert LEGACY.has("uploads:write")
    assert LEGACY.has("runs:create:live:upload")
    assert not LEGACY.has("registry:publish")
