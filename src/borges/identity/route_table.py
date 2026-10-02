from __future__ import annotations

import re
from typing import Final

from borges.identity import scopes as s

OPEN: Final = "open"

RouteRequirement = str | tuple[str, ...]

RUN_CREATE_SCOPES: Final = (
    s.RUNS_CREATE_SCRIPTED,
    s.RUNS_CREATE_LIVE_CURATED,
    s.RUNS_CREATE_LIVE_UPLOAD,
)

ROUTE_TABLE: Final[dict[tuple[str, str], RouteRequirement]] = {
    ("GET", "/api/health"): OPEN,
    ("GET", "/api/me"): OPEN,
    ("GET", "/api/cases"): s.CASES_READ,
    ("GET", "/api/cases/{case_id}"): s.CASES_READ,
    ("GET", "/api/cases/{case_id}/recording"): s.RECORDINGS_READ,
    ("GET", "/api/agents"): s.CASES_READ,
    ("GET", "/api/agents/{agent_id}"): s.CASES_READ,
    ("GET", "/api/agents/{agent_id}/versions/{version}"): s.CASES_READ,
    ("POST", "/api/agents/publish"): s.REGISTRY_PUBLISH,
    ("POST", "/api/agents/{agent_id}/versions/{version}/approve"): s.REGISTRY_APPROVE,
    ("GET", "/api/runs"): s.RUNS_READ,
    ("POST", "/api/runs"): RUN_CREATE_SCOPES,
    ("GET", "/api/runs/{run_id}"): s.RUNS_READ,
    ("GET", "/api/runs/{run_id}/events"): s.RUNS_READ,
    ("GET", "/api/runs/{run_id}/universes/{universe_id}"): s.RUNS_READ,
    ("GET", "/api/runs/{run_id}/universes/{universe_id}/script"): s.RUNS_READ,
    ("GET", "/api/runs/{run_id}/trace"): s.RUNS_READ,
    ("GET", "/api/runs/{run_id}/audit"): s.RUNS_READ,
    ("POST", "/api/uploads"): s.UPLOADS_WRITE,
    ("GET", "/api/audit"): s.AUDIT_READ,
}


def _compile(template: str) -> re.Pattern[str]:
    return re.compile(re.sub(r"\{[^/}]+\}", "[^/]+", template))


_MATCHERS: Final = sorted(
    (
        (method, template, _compile(template), requirement)
        for (method, template), requirement in ROUTE_TABLE.items()
    ),
    key=lambda item: item[1].count("{"),
)


def match_route(method: str, path: str) -> tuple[str, RouteRequirement] | None:
    for declared, template, pattern, requirement in _MATCHERS:
        if declared == method.upper() and pattern.fullmatch(path):
            return template, requirement
    return None


def requirement_for(method: str, route_path: str) -> RouteRequirement | None:
    return ROUTE_TABLE.get((method.upper(), route_path))


def scope_label(requirement: RouteRequirement) -> str:
    return requirement if isinstance(requirement, str) else " or ".join(requirement)
