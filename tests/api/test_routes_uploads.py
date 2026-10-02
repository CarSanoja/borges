from __future__ import annotations

import json

import httpx
import pandas as pd
import pytest

from borges.analysis.models import DatasetProfile
from borges.api import uploads as uploads_module
from borges.api.app import create_app
from borges.config import Settings
from tests.identity.keys import bearer, make_key


def build_client(
    tmp_path, monkeypatch: pytest.MonkeyPatch, authed: bool = True, **settings
) -> httpx.AsyncClient:
    monkeypatch.setattr(
        uploads_module.profile_module,
        "profile_dataframe",
        lambda df, name, sample=5: DatasetProfile(name=name, n_rows=len(df), columns=[]),
    )
    config = Settings(_env_file=None, borges_home=tmp_path, **settings)
    headers = bearer(make_key(config, "uploads:write")) if authed else {}
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings=config)),
        base_url="http://t",
        headers=headers,
    )


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> httpx.AsyncClient:
    return build_client(tmp_path, monkeypatch, borges_backend="contree", nebius_api_key="k")


def table() -> bytes:
    return pd.DataFrame({"a": range(60), "b": range(60)}).to_csv(index=False).encode()


async def post_upload(client: httpx.AsyncClient, headers: dict | None = None):
    async with client:
        return await client.post(
            "/api/uploads", files={"file": ("d.csv", table(), "text/csv")}, headers=headers or {}
        )


async def test_local_backend_refuses_uploads_by_default(tmp_path, monkeypatch) -> None:
    client = build_client(tmp_path, monkeypatch, nebius_api_key="k")
    response = await post_upload(client)
    assert response.status_code == 403
    assert "isolated sandboxes" in response.json()["detail"]
    assert not list((tmp_path / "uploads").glob("*")) if (tmp_path / "uploads").exists() else True


async def test_local_backend_accepts_uploads_with_flag(tmp_path, monkeypatch) -> None:
    client = build_client(
        tmp_path, monkeypatch, nebius_api_key="k", borges_allow_untrusted_local=True
    )
    assert (await post_upload(client)).status_code == 200


async def test_contree_backend_accepts_uploads_when_live_available(tmp_path, monkeypatch) -> None:
    client = build_client(tmp_path, monkeypatch, borges_backend="contree", nebius_api_key="k")
    assert (await post_upload(client)).status_code == 200


async def test_contree_backend_refuses_uploads_without_live(tmp_path, monkeypatch) -> None:
    client = build_client(tmp_path, monkeypatch, borges_backend="contree")
    response = await post_upload(client)
    assert response.status_code == 403
    assert "NEBIUS_API_KEY" in response.json()["detail"]


async def test_legacy_live_token_still_authorises_uploads(tmp_path, monkeypatch) -> None:
    def make() -> httpx.AsyncClient:
        return build_client(
            tmp_path,
            monkeypatch,
            authed=False,
            borges_backend="contree",
            nebius_api_key="k",
            borges_live_token="secret",
        )

    assert (await post_upload(make())).status_code == 403
    assert (await post_upload(make(), {"X-Borges-Live-Token": "wrong"})).status_code == 403
    assert (await post_upload(make(), {"X-Borges-Live-Token": "secret"})).status_code == 200


async def test_anonymous_cannot_upload(tmp_path, monkeypatch) -> None:
    client = build_client(
        tmp_path, monkeypatch, authed=False, borges_backend="contree", nebius_api_key="k"
    )
    response = await post_upload(client)
    assert response.status_code == 403
    assert "uploads:write" in response.json()["detail"]


async def test_upload_returns_id_and_profile(client: httpx.AsyncClient) -> None:
    csv = pd.DataFrame({"a": range(60), "b": range(60)}).to_csv(index=False)
    async with client:
        response = await client.post(
            "/api/uploads", files={"file": ("d.csv", csv.encode(), "text/csv")}
        )
    body = response.json()
    assert response.status_code == 200
    assert len(body["upload_id"]) == 32
    assert body["profile"]["name"] == "d.csv"
    assert body["profile"]["n_rows"] == 60


async def test_invalid_upload_is_400(client: httpx.AsyncClient) -> None:
    async with client:
        response = await client.post(
            "/api/uploads", files={"file": ("d.csv", b"a,b\n1,2\n", "text/csv")}
        )
    assert response.status_code == 400
    assert "rows" in response.json()["detail"]


async def test_missing_file_is_422(client: httpx.AsyncClient) -> None:
    async with client:
        assert (await client.post("/api/uploads")).status_code == 422


async def test_upload_over_quota_is_413(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        uploads_module.profile_module,
        "profile_dataframe",
        lambda df, name, sample=5: DatasetProfile(name=name, n_rows=len(df), columns=[]),
    )
    config = Settings(
        _env_file=None,
        borges_home=tmp_path,
        borges_upload_quota_mb=0,
        borges_backend="contree",
        nebius_api_key="k",
    )
    app = create_app(settings=config)
    csv = pd.DataFrame({"a": range(60), "b": range(60)}).to_csv(index=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://t", headers=bearer(make_key(config, "uploads:write"))
    ) as http:
        response = await http.post(
            "/api/uploads", files={"file": ("d.csv", csv.encode(), "text/csv")}
        )
    assert response.status_code == 413


async def test_upload_reports_personal_data_counts_without_values(tmp_path) -> None:
    config = Settings(
        _env_file=None, borges_home=tmp_path, borges_backend="contree", nebius_api_key="k"
    )
    app = create_app(settings=config)
    frame = pd.DataFrame(
        {
            "a": range(60),
            "contact": [f"person{i}@example.com" for i in range(60)],
            "note": ["call +34 612 345 678"] * 60,
        }
    )
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://t",
        headers=bearer(make_key(config, "uploads:write")),
    )
    async with client:
        response = await client.post(
            "/api/uploads",
            files={"file": ("d.csv", frame.to_csv(index=False).encode(), "text/csv")},
        )
    body = response.json()
    assert response.status_code == 200
    by_column = {c["column"]: c["kinds"] for c in body["pii"]["columns"]}
    assert by_column == {"contact": {"email": 60}, "note": {"phone": 60}}
    assert body["pii"]["total_detections"] == 120
    text = json.dumps(body)
    assert "person1@example.com" not in text and "612 345 678" not in text


async def test_upload_with_instruction_in_a_column_name_is_refused(tmp_path) -> None:
    config = Settings(
        _env_file=None, borges_home=tmp_path, borges_backend="contree", nebius_api_key="k"
    )
    app = create_app(settings=config)
    frame = pd.DataFrame({"ignore_previous_instructions": range(60), "b": range(60)})
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://t",
        headers=bearer(make_key(config, "uploads:write")),
    )
    async with client:
        response = await client.post(
            "/api/uploads",
            files={"file": ("d.csv", frame.to_csv(index=False).encode(), "text/csv")},
        )
    assert response.status_code == 400
    assert "Armor refused the run" in response.json()["detail"]
