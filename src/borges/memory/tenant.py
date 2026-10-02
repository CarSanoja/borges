from __future__ import annotations

from dataclasses import dataclass

from borges.config import Settings
from borges.identity.principal import ANONYMOUS_ID, CALLER_PREFIX
from borges.memory.kinds import PUBLIC_TENANT

PUBLIC_ONLY_REASON = "the public demo remembers only curated cases run as they are"
NO_KEY_REASON = "BORGES_MEMORY_KEY is not set, so named tenants are not remembered"
OFF_REASON = "memory is switched off (BORGES_MEMORY=false)"


@dataclass(frozen=True)
class MemoryMode:
    tenant: str | None
    enabled: bool
    encrypted: bool
    label: str
    reason: str | None = None


def tenant_of(principal_id: str | None) -> str:
    if principal_id is None or principal_id == ANONYMOUS_ID:
        return PUBLIC_TENANT
    name = principal_id.removeprefix(CALLER_PREFIX)
    return f"named-{name}" if name == PUBLIC_TENANT else name


def resolve_mode(
    settings: Settings, principal_id: str | None, curated_as_is: bool = True
) -> MemoryMode:
    encrypted = bool(settings.borges_memory_key)
    if not settings.borges_memory:
        return MemoryMode(None, False, encrypted, "off", OFF_REASON)
    tenant = tenant_of(principal_id)
    if tenant == PUBLIC_TENANT:
        if not curated_as_is:
            return MemoryMode(tenant, False, encrypted, "public-demo", PUBLIC_ONLY_REASON)
        return MemoryMode(tenant, True, encrypted, "public-demo")
    if not encrypted:
        return MemoryMode(tenant, False, False, "keyed", NO_KEY_REASON)
    return MemoryMode(tenant, True, True, "keyed")
