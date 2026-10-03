from __future__ import annotations

from typing import Any

from fastapi import Request

from borges.config import Settings
from borges.fleet.catalog import build_catalog
from borges.fleet.locations import open_store
from borges.identity.keystore import open_keystore
from borges.identity.principal import Principal
from borges.identity.scopes import PUBLIC_SCOPES
from borges.memory import service
from borges.memory.db import db_path, open_memory_db
from borges.memory.kinds import PUBLIC_TENANT, MemoryKind
from borges.memory.tenant import resolve_mode


def registry(settings: Settings) -> dict[str, Any]:
    catalog = build_catalog(settings, [])
    summary = catalog.summary
    chain = open_store(settings).verify()
    approved = summary.by_approval.get("approved", 0)
    blocked = len(summary.blocked)
    status = "ok" if chain.ok and blocked == 0 else "attention"
    return {
        "status": status if chain.ok else "error",
        "summary": f"{summary.total} agents and components, {approved} at an approved version, "
        f"enforcement {'on' if summary.enforce else 'off'}.",
        "facts": {
            "agents": summary.total,
            "approved_versions": approved,
            "by_approval": summary.by_approval,
            "by_lifecycle": summary.by_lifecycle,
            "unapproved_blocking": blocked,
            "enforce": summary.enforce,
            "four_eyes": settings.borges_registry_four_eyes,
            "registry_sha": catalog.registry_sha,
            "chain_ok": chain.ok,
            "chain_keyed": chain.keyed,
            "chain_records": chain.records,
        },
    }


def runtime(request: Request, settings: Settings) -> dict[str, Any]:
    live = request.app.state.runtime
    if live is None:
        return {
            "status": "off",
            "summary": "The run queue is not attached to this server.",
            "facts": {"queue": False},
        }
    stats = live.stats()
    dead = int(stats["dead_letter_count"] or 0)
    return {
        "status": "attention" if dead else "ok",
        "summary": f"{stats['queue_depth']} queued, {stats['active_workers']} running, "
        f"{dead} in dead-letter.",
        "facts": {
            "queue": True,
            "queue_depth": stats["queue_depth"],
            "active_workers": stats["active_workers"],
            "oldest_job_age_s": stats["oldest_job_age_s"],
            "dead_letter_count": dead,
            "resume_from_checkpoints": True,
            "lease_s": settings.borges_job_lease_s,
            "max_attempts": settings.borges_job_max_attempts,
            "scheduler": settings.borges_scheduler,
        },
    }


def _tenant_count(settings: Settings) -> int:
    conn = open_memory_db(db_path(settings))
    try:
        selects = " UNION ".join(f"SELECT tenant FROM {kind.table}" for kind in MemoryKind)
        rows = conn.execute(f"SELECT DISTINCT tenant FROM ({selects})").fetchall()
    finally:
        conn.close()
    return len([row for row in rows if row["tenant"] != PUBLIC_TENANT])


def memory(settings: Settings, principal: Principal) -> dict[str, Any]:
    mode = resolve_mode(settings, None)
    public = service.describe(settings, None)
    facts: dict[str, Any] = {
        "enabled": settings.borges_memory,
        "encrypted": bool(settings.borges_memory_key),
        "public_demo": {"totals": public["totals"], "datasets": len(public["datasets"])},
    }
    if not principal.anonymous:
        facts["tenants"] = _tenant_count(settings)
        facts["caller"] = {"tenant": service.describe(settings, principal.id)["tenant"]}
    if not settings.borges_memory:
        status, text = "off", mode.reason or "memory is off"
    elif not settings.borges_memory_key:
        status, text = (
            "attention",
            "Public demo memory only, unencrypted: no memory key set.",
        )
    else:
        status, text = "ok", "Encrypted per-tenant memory is on."
    return {"status": status, "summary": text, "facts": facts}


def identity(settings: Settings, principal: Principal) -> dict[str, Any]:
    keystore = open_keystore(settings).verify()
    return {
        "status": "ok" if keystore.ok else "error",
        "summary": f"You are {principal.id} with {len(principal.scopes)} scopes; "
        f"the key store is {'HMAC-keyed' if keystore.keyed else 'unkeyed'} and "
        f"{'intact' if keystore.ok else 'broken'}.",
        "facts": {
            "principal": principal.id,
            "kind": principal.kind,
            "scopes": sorted(principal.scopes),
            "anonymous_scopes": sorted(PUBLIC_SCOPES),
            "keystore": {
                "ok": keystore.ok,
                "keyed": keystore.keyed,
                "anchored": keystore.anchored,
                "records": keystore.records,
            },
            "agent_token_ttl_s": settings.borges_agent_token_ttl_s,
        },
    }
