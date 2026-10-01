from __future__ import annotations

import httpx
import pandas as pd
import pytest

from borges.analysis.models import DatasetProfile
from borges.api import uploads as uploads_module
from borges.api.app import create_app
from borges.config import Settings


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> httpx.AsyncClient:
    monkeypatch.setattr(
        uploads_module.profile_module,
        "profile_dataframe",
        lambda df, name, sample=5: DatasetProfile(name=name, n_rows=len(df), columns=[]),
    )
    app = create_app(settings=Settings(borges_home=tmp_path))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


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
    app = create_app(settings=Settings(borges_home=tmp_path, borges_upload_quota_mb=0))
    csv = pd.DataFrame({"a": range(60), "b": range(60)}).to_csv(index=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as http:
        response = await http.post(
            "/api/uploads", files={"file": ("d.csv", csv.encode(), "text/csv")}
        )
    assert response.status_code == 413
