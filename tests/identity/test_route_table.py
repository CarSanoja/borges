from __future__ import annotations

from borges.api.app import create_app
from borges.config import Settings
from borges.identity.route_table import OPEN, ROUTE_TABLE, match_route, requirement_for, scope_label
from borges.identity.scopes import KNOWN_SCOPES


def test_every_api_route_of_the_app_is_declared(tmp_path) -> None:
    app = create_app(settings=Settings(_env_file=None, borges_home=tmp_path))
    missing = []
    for path, operations in app.openapi()["paths"].items():
        for method in operations:
            if match_route(method, path) is None:
                missing.append((method, path))
    assert missing == []


def test_templates_match_concrete_paths() -> None:
    assert match_route("GET", "/api/runs/abc/trace")[0] == "/api/runs/{run_id}/trace"
    assert match_route("POST", "/api/agents/publish")[0] == "/api/agents/publish"
    assert match_route("GET", "/api/runs/a/b") is None
    assert match_route("GET", "/api/runs/") is None


def test_every_declared_scope_is_known() -> None:
    for requirement in ROUTE_TABLE.values():
        scopes = {requirement} if isinstance(requirement, str) else set(requirement)
        assert scopes <= KNOWN_SCOPES | {OPEN}


def test_unknown_route_has_no_requirement() -> None:
    assert requirement_for("GET", "/api/secret") is None
    assert requirement_for("DELETE", "/api/runs") is None


def test_label_joins_alternatives() -> None:
    assert scope_label(("a", "b")) == "a or b"
    assert scope_label("a") == "a"


def test_runtime_routes_are_declared() -> None:
    assert requirement_for("GET", "/api/runs/dead-letter") == "admin"
    assert requirement_for("GET", "/api/schedules") == "admin"
    cancel = requirement_for("POST", "/api/runs/{run_id}/cancel")
    assert isinstance(cancel, tuple) and "runs:create:scripted" in cancel
    assert match_route("GET", "/api/runs/dead-letter")[0] == "/api/runs/dead-letter"
    assert match_route("POST", "/api/runs/r_1/cancel")[0] == "/api/runs/{run_id}/cancel"


def test_memory_routes_are_declared() -> None:
    assert requirement_for("GET", "/api/memory") == "memory:read"
    assert requirement_for("DELETE", "/api/memory") == "memory:write"
    assert requirement_for("POST", "/api/memory/notes") == "memory:write"
