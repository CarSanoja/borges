from __future__ import annotations

CASES_READ = "cases:read"
RUNS_READ = "runs:read"
RUNS_CREATE_SCRIPTED = "runs:create:scripted"
RUNS_CREATE_LIVE_CURATED = "runs:create:live:curated"
RECORDINGS_READ = "recordings:read"
MEMORY_READ = "memory:read"

UPLOADS_WRITE = "uploads:write"
RUNS_CREATE_LIVE_UPLOAD = "runs:create:live:upload"
REGISTRY_PUBLISH = "registry:publish"
REGISTRY_APPROVE = "registry:approve"
AUDIT_READ = "audit:read"
MEMORY_WRITE = "memory:write"
ADMIN = "admin"

PUBLIC_SCOPES: frozenset[str] = frozenset(
    {
        CASES_READ,
        RUNS_READ,
        RUNS_CREATE_SCRIPTED,
        RUNS_CREATE_LIVE_CURATED,
        RECORDINGS_READ,
        MEMORY_READ,
    }
)
NAMED_ONLY_SCOPES: frozenset[str] = frozenset(
    {
        UPLOADS_WRITE,
        RUNS_CREATE_LIVE_UPLOAD,
        REGISTRY_PUBLISH,
        REGISTRY_APPROVE,
        AUDIT_READ,
        MEMORY_WRITE,
        ADMIN,
    }
)
KNOWN_SCOPES: frozenset[str] = PUBLIC_SCOPES | NAMED_ONLY_SCOPES

LEGACY_TOKEN_SCOPES: frozenset[str] = frozenset({UPLOADS_WRITE, RUNS_CREATE_LIVE_UPLOAD})


class UnknownScope(ValueError):
    pass


def parse_scopes(raw: str) -> frozenset[str]:
    scopes = frozenset(part.strip() for part in raw.split(",") if part.strip())
    unknown = sorted(scopes - KNOWN_SCOPES)
    if unknown:
        known = ", ".join(sorted(KNOWN_SCOPES))
        raise UnknownScope(f"unknown scope(s): {', '.join(unknown)}; known scopes: {known}")
    if not scopes:
        raise UnknownScope("at least one scope is required")
    return scopes
