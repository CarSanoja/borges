from __future__ import annotations

import sys
import types

import httpx
import pytest

from borges.api.app import create_app
from borges.config import Settings


def make_client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


@pytest.fixture
def dist(tmp_path):
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<html>spa</html>")
    (root / "assets" / "app.js").write_text("console.log(1)")
    (root / "favicon.svg").write_text("<svg/>")
    return root


async def test_spa_serves_assets_and_falls_back(tmp_path, dist) -> None:
    app = create_app(settings=Settings(borges_home=tmp_path, borges_frontend_dist=dist))
    async with make_client(app) as client:
        assert (await client.get("/assets/app.js")).text == "console.log(1)"
        assert (await client.get("/favicon.svg")).text == "<svg/>"
        assert "spa" in (await client.get("/")).text
        assert "spa" in (await client.get("/run/abc")).text
        assert (await client.get("/api/nothing")).status_code == 404
        assert (await client.get("/api/health")).json()["status"] == "ok"


async def test_spa_blocks_path_traversal(tmp_path, dist) -> None:
    (tmp_path / "secret.txt").write_text("secret")
    app = create_app(settings=Settings(borges_home=tmp_path, borges_frontend_dist=dist))
    async with make_client(app) as client:
        response = await client.get("/..%2fsecret.txt")
    assert "secret" not in response.text


async def test_no_frontend_means_no_fallback(tmp_path) -> None:
    app = create_app(settings=Settings(borges_home=tmp_path, borges_frontend_dist=tmp_path / "x"))
    async with make_client(app) as client:
        assert (await client.get("/anything")).status_code == 404


async def test_cors_allows_dev_origin(tmp_path) -> None:
    app = create_app(settings=Settings(borges_home=tmp_path))
    async with make_client(app) as client:
        response = await client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        other = await client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in other.headers


async def test_lifespan_builds_missing_objects(tmp_path, monkeypatch) -> None:
    built: dict[str, object] = {}

    def fake(name: str, cls: str):
        class Fake:
            def __init__(self, *args: object) -> None:
                built[cls] = args

        module = types.ModuleType(name)
        setattr(module, cls, Fake)
        monkeypatch.setitem(sys.modules, name, module)

    fake("borges.cases.registry", "CaseRegistry")
    fake("borges.runs.bus", "EventBus")
    fake("borges.runs.orchestrator", "RunOrchestrator")
    fake("borges.runs.store", "RunStore")
    settings = Settings(borges_home=tmp_path)
    injected = types.SimpleNamespace(interrupt_running=lambda active: [])
    app = create_app(settings=settings, store=injected)
    async with app.router.lifespan_context(app):
        assert app.state.store is injected
        assert built["CaseRegistry"] == (settings.borges_cases_dir,)
        assert built["EventBus"] == (injected,)
        assert len(built["RunOrchestrator"]) == 4
        assert built["RunOrchestrator"][1] is injected
