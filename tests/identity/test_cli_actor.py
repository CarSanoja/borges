from __future__ import annotations

import pytest

from borges.config import Settings
from borges.identity.cli_actor import ActorError, resolve_actor
from tests.identity.keys import make_key


def test_without_key_the_default_or_declared_actor_is_used(settings: Settings) -> None:
    assert resolve_actor(settings, "registry:approve", None, None, False).principal_id == "operator"
    declared = resolve_actor(settings, "registry:approve", None, "caller://bob", False)
    assert declared.principal_id == "caller://bob" and not declared.authenticated


def test_required_key_is_enforced(settings: Settings) -> None:
    with pytest.raises(ActorError, match="registry:approve"):
        resolve_actor(settings, "registry:approve", None, "caller://bob", True)


def test_key_supplies_the_principal(settings: Settings) -> None:
    token = make_key(settings, "registry:approve", "bob")
    actor = resolve_actor(settings, "registry:approve", token, None, True)
    assert actor.principal_id == "caller://bob" and actor.authenticated


def test_key_without_the_scope_or_invalid_is_rejected(settings: Settings) -> None:
    token = make_key(settings, "audit:read", "bob")
    with pytest.raises(ActorError, match="does not hold"):
        resolve_actor(settings, "registry:approve", token, None, True)
    with pytest.raises(ActorError, match="rejected"):
        resolve_actor(settings, "registry:approve", "bk_x_y", None, True)


def test_admin_key_satisfies_any_scope(settings: Settings) -> None:
    token = make_key(settings, "admin", "root")
    assert resolve_actor(settings, "registry:approve", token, None, True).authenticated
