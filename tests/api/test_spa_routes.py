from __future__ import annotations

import httpx
import pytest

from borges.api.app import create_app
from borges.api.spa import is_client_route
from borges.config import Settings


@pytest.fixture
def client(tmp_path):
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<html>spa</html>")
    (root / "og.svg").write_text("<svg/>")
    app = create_app(settings=Settings(borges_home=tmp_path, borges_frontend_dist=root))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


@pytest.mark.parametrize(
    "path", ["/", "/replay/red_cards", "/run/r_20261002T033827_17e789", "/run/abc/"]
)
async def test_known_client_routes_return_200_with_the_app(client, path) -> None:
    async with client:
        response = await client.get(path)
    assert response.status_code == 200
    assert "spa" in response.text


@pytest.mark.parametrize("path", ["/nope", "/run", "/run/a/b", "/replay", "/runs/abc", "/admin/x"])
async def test_unknown_routes_return_404_with_the_app_html(client, path) -> None:
    async with client:
        response = await client.get(path)
    assert response.status_code == 404
    assert "spa" in response.text


async def test_static_files_and_api_keep_their_status(client) -> None:
    async with client:
        assert (await client.get("/og.svg")).status_code == 200
        assert (await client.get("/api/health")).status_code == 200
        assert (await client.get("/api/nothing")).status_code == 404


def test_route_matcher_is_exact() -> None:
    assert is_client_route("")
    assert is_client_route("replay/x")
    assert not is_client_route("replay/x/y")
    assert not is_client_route("favicon.ico")
