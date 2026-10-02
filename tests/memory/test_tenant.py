from __future__ import annotations

from borges.config import Settings
from borges.identity.principal import ANONYMOUS_ID, caller_principal
from borges.memory.tenant import resolve_mode, tenant_of


def cfg(**extra) -> Settings:
    return Settings(_env_file=None, borges_memory=True, **extra)


def test_tenant_of_maps_principals() -> None:
    assert tenant_of(None) == "public-demo"
    assert tenant_of(ANONYMOUS_ID) == "public-demo"
    assert tenant_of(caller_principal("acme")) == "acme"
    assert tenant_of(caller_principal("public-demo")) == "named-public-demo"


def test_memory_can_be_switched_off() -> None:
    mode = resolve_mode(Settings(_env_file=None), None)
    assert mode.enabled is False and mode.label == "off" and mode.tenant is None


def test_anonymous_callers_share_the_public_tenant_for_curated_cases_only() -> None:
    mode = resolve_mode(cfg(), ANONYMOUS_ID)
    assert (mode.tenant, mode.enabled, mode.encrypted, mode.label) == (
        "public-demo",
        True,
        False,
        "public-demo",
    )
    modified = resolve_mode(cfg(), ANONYMOUS_ID, curated_as_is=False)
    assert modified.enabled is False and "curated" in (modified.reason or "")


def test_public_memory_is_encrypted_when_a_key_exists() -> None:
    assert resolve_mode(cfg(borges_memory_key="k"), None).encrypted is True


def test_named_tenants_need_the_key() -> None:
    off = resolve_mode(cfg(), caller_principal("acme"))
    assert off.enabled is False and "BORGES_MEMORY_KEY" in (off.reason or "")
    on = resolve_mode(cfg(borges_memory_key="k"), caller_principal("acme"))
    assert (on.tenant, on.enabled, on.encrypted, on.label) == ("acme", True, True, "keyed")
