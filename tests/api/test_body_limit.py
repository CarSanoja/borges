from __future__ import annotations

import httpx

from borges.api.body_limit import MAX_JSON_BYTES
from tests.api.test_routes_runs import Env


async def test_an_oversized_json_body_is_refused_before_parsing(tmp_path) -> None:
    env = Env(tmp_path, key=None)
    body = b'{"case_id": "a", "question": "' + b"x" * (MAX_JSON_BYTES + 10) + b'"}'
    async with env.client() as client:
        declared = await client.post(
            "/api/runs", content=body, headers={"content-type": "application/json"}
        )
    assert declared.status_code == 413
    assert not env.orchestrator.calls


async def test_a_chunked_body_is_counted_as_it_arrives(tmp_path) -> None:
    env = Env(tmp_path, key=None)

    async def chunks():
        yield b'{"case_id": "a", "question": "'
        for _ in range(MAX_JSON_BYTES // 1024 + 2):
            yield b"x" * 1024
        yield b'"}'

    async with env.client() as client:
        response = await client.post(
            "/api/runs", content=chunks(), headers={"content-type": "application/json"}
        )
    assert response.status_code == 413
    assert not env.orchestrator.calls


async def test_normal_requests_and_uploads_are_unaffected(tmp_path) -> None:
    env = Env(tmp_path, key=None)
    async with env.client() as client:
        ok = await client.post("/api/runs", json={"case_id": "a"})
        bad_length = await client.post(
            "/api/runs", content=b"{}", headers={"content-length": "abc"}
        )
    assert ok.status_code == 202
    assert isinstance(bad_length, httpx.Response) and bad_length.status_code in (400, 413, 422)
