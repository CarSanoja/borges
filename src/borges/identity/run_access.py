from __future__ import annotations

from typing import Any

from borges.identity.principal import ANONYMOUS_ID, Principal
from borges.identity.scopes import ADMIN


def run_is_public(case_id: str | None, upload: bool, principal: Principal) -> bool:
    return case_id is not None and not upload and principal.anonymous


def meta_is_public(meta: dict[str, Any]) -> bool:
    declared = meta.get("public")
    if isinstance(declared, bool):
        return declared
    owner = meta.get("principal")
    return meta.get("case_id") is not None and owner in (None, ANONYMOUS_ID)


def owns_run(meta: dict[str, Any], principal: Principal) -> bool:
    owner = meta.get("principal")
    return isinstance(owner, str) and owner == principal.id and not principal.anonymous


def can_read_run(meta: dict[str, Any], principal: Principal) -> bool:
    if principal.has(ADMIN):
        return True
    return meta_is_public(meta) or owns_run(meta, principal)


def can_share_run(meta: dict[str, Any], principal: Principal) -> bool:
    return principal.has(ADMIN) or owns_run(meta, principal)
