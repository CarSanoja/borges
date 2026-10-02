from __future__ import annotations

from dataclasses import dataclass

from borges.config import Settings
from borges.identity.keystore import open_keystore
from borges.identity.principal import Principal

DEFAULT_ACTOR = "operator"


class ActorError(ValueError):
    pass


@dataclass(frozen=True)
class Actor:
    principal_id: str
    authenticated: bool


def resolve_actor(
    settings: Settings, scope: str, key: str | None, as_principal: str | None, require_key: bool
) -> Actor:
    principal: Principal | None = None
    if key:
        record, failure = open_keystore(settings).authenticate(key)
        if record is None:
            raise ActorError(f"the API key was rejected ({failure})")
        principal = record.principal()
        if not principal.has(scope):
            raise ActorError(f"the key for {principal.id} does not hold the {scope} scope")
    elif require_key:
        raise ActorError(
            f"BORGES_REGISTRY_FOUR_EYES=true: this action needs an API key with the {scope} "
            "scope (--key or BORGES_API_KEY)"
        )
    if principal is not None:
        if as_principal and as_principal != principal.id:
            raise ActorError(
                f"--as {as_principal} does not match the key's principal {principal.id}"
            )
        return Actor(principal.id, True)
    return Actor(as_principal or DEFAULT_ACTOR, False)
