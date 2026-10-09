from __future__ import annotations

import json

import pytest

from borges.telemetry.run_telemetry import global_audit_path
from tests.api.test_routes_runs import Env
from tests.identity.keys import bearer, make_key

CASE = {"case_id": "a", "llm": "nebius"}
UPLOAD = {
    "upload_id": "u" * 32,
    "llm": "nebius",
    "question": "q?",
    "decision_rule": {"metric": "effect"},
}


def stub_upload(env: Env) -> None:
    env.app.state.uploads.get = lambda upload_id: (b"PQ", "d.csv")


def uploader(env: Env) -> dict[str, str]:
    return bearer(make_key(env.app.state.settings, "runs:create:live:upload"))


async def post(env: Env, body: dict, headers: dict | None = None):
    async with env.client() as client:
        return await client.post("/api/runs", json=body, headers=headers or {})


async def test_live_local_upload_is_rejected_by_default(tmp_path) -> None:
    env = Env(tmp_path, key="k")
    stub_upload(env)
    response = await post(env, UPLOAD, uploader(env))
    assert response.status_code == 400
    assert "isolated sandboxes" in response.json()["detail"]
    assert env.orchestrator.calls == []


async def test_live_local_question_override_is_rejected(tmp_path) -> None:
    env = Env(tmp_path, key="k")
    response = await post(env, {**CASE, "question": "Does the new variant raise conversion?"})
    assert response.status_code == 400
    assert "own question" in response.json()["detail"]


async def test_live_local_rule_override_is_rejected(tmp_path) -> None:
    env = Env(tmp_path, key="k")
    response = await post(env, {**CASE, "decision_rule": {"metric": "m"}})
    assert response.status_code == 400


async def test_live_curated_case_without_overrides_is_accepted(tmp_path) -> None:
    env = Env(tmp_path, key="k")
    assert (await post(env, CASE)).status_code == 202


async def test_flag_lets_live_local_upload_through(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_allow_untrusted_local=True)
    stub_upload(env)
    assert (await post(env, UPLOAD, uploader(env))).status_code == 202


async def test_contree_server_accepts_live_upload(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_backend="contree")
    stub_upload(env)
    assert (await post(env, UPLOAD, uploader(env))).status_code == 202


async def test_live_token_gates_uploads(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_allow_untrusted_local=True, borges_live_token="s3cret")
    stub_upload(env)
    assert (await post(env, UPLOAD)).status_code == 403
    assert (await post(env, UPLOAD, {"X-Borges-Live-Token": "bad"})).status_code == 403
    assert (await post(env, UPLOAD, {"X-Borges-Live-Token": "s3cret"})).status_code == 202


async def test_client_backend_different_from_server_is_400(tmp_path) -> None:
    env = Env(tmp_path, key=None)
    response = await post(env, {"case_id": "a", "backend": "contree"})
    assert response.status_code == 400
    assert "runs the local backend" in response.json()["detail"]
    assert (await post(env, {"case_id": "a", "backend": "local"})).status_code == 202


async def test_max_universes_is_clamped_to_the_server_setting(tmp_path) -> None:
    env = Env(tmp_path, key=None, borges_max_universes=7)
    await post(env, {"case_id": "a", "max_universes": 150})
    await post(env, {"case_id": "a"})
    await post(env, {"case_id": "a", "max_universes": 3})
    assert [c[0].max_universes for c in env.orchestrator.calls] == [7, 7, 3]


async def test_active_run_cap_applies_to_scripted_runs(tmp_path) -> None:
    env = Env(tmp_path, key=None, borges_max_active_runs=2)
    env.orchestrator.active = 2
    response = await post(env, {"case_id": "a", "llm": "scripted"})
    assert response.status_code == 429
    assert "already running 2 analyses" in response.json()["detail"]
    assert "recorded run" in response.json()["detail"]
    env.orchestrator.active = 1
    assert (await post(env, {"case_id": "a"})).status_code == 202


async def test_upload_with_scripted_llm_is_400(tmp_path) -> None:
    env = Env(tmp_path, key=None)
    stub_upload(env)
    response = await post(env, {**UPLOAD, "llm": "scripted"}, uploader(env))
    assert response.status_code == 400
    assert "need live mode" in response.json()["detail"]


async def test_spent_budget_is_403(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_spend_cap_usd=1.0)
    (tmp_path / "spend.json").write_text(json.dumps({"total_usd": 1.0}))
    response = await post(env, CASE)
    assert response.status_code == 403
    assert "budget" in response.json()["detail"]


async def test_scripted_runs_ignore_the_budget(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_spend_cap_usd=1.0)
    (tmp_path / "spend.json").write_text(json.dumps({"total_usd": 5.0}))
    assert (await post(env, {"case_id": "a", "llm": "scripted"})).status_code == 202


async def test_non_ascii_live_token_is_403_not_500(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_allow_untrusted_local=True, borges_live_token="s3cret")
    stub_upload(env)
    response = await post(env, UPLOAD, {"X-Borges-Live-Token": "s\xe9".encode("latin-1")})
    assert response.status_code == 403


async def test_local_llm_is_refused_over_http(tmp_path) -> None:
    env = Env(tmp_path, key="k")
    response = await post(env, {"case_id": "a", "llm": "local"})
    assert response.status_code == 400
    assert "CLI only" in response.json()["detail"]
    assert env.orchestrator.calls == []


async def test_live_run_is_refused_when_the_registry_has_no_approval(tmp_path, caplog) -> None:
    env = Env(tmp_path, key="k", borges_registry_enforce=True)
    from borges.analysis.prompts import judge

    original = judge.SYSTEM
    judge.SYSTEM = original + " Be stricter."
    try:
        response = await post(env, CASE)
    finally:
        judge.SYSTEM = original
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail == (
        "This server's analysis agents are being updated, so live runs are paused; try again later."
    )
    assert env.orchestrator.calls == []
    operator = global_audit_path(env.app.state.settings).read_text()
    assert "borges agents publish" in operator and "judge" in operator
    assert "borges agents publish" in caplog.text


async def test_live_run_is_accepted_when_the_registry_approves_the_tree(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_registry_enforce=True)
    assert (await post(env, CASE)).status_code == 202


async def test_scripted_run_ignores_registry_enforcement(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_registry_enforce=True)
    from borges.analysis.prompts import judge

    original = judge.SYSTEM
    judge.SYSTEM = original + " Be stricter."
    try:
        response = await post(env, {"case_id": "a", "llm": "scripted"})
    finally:
        judge.SYSTEM = original
    assert response.status_code == 202


async def test_unknown_upload_is_reported_even_when_the_server_is_busy(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_max_active_runs=1)
    env.orchestrator.active = 1
    response = await post(env, UPLOAD, uploader(env))
    assert response.status_code == 400
    assert "Unknown upload" in response.json()["detail"]


async def test_busy_message_for_an_upload_does_not_mention_a_recorded_run(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_max_active_runs=1, borges_allow_untrusted_local=True)
    stub_upload(env)
    env.orchestrator.active = 1
    response = await post(env, UPLOAD, uploader(env))
    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Borges is already running 1 analyses, the most this server allows; try again in a minute."
    )


@pytest.mark.parametrize("alpha", [0, 1, -0.5, 7])
async def test_bad_alpha_is_reported_before_the_busy_gate(tmp_path, alpha: float) -> None:
    env = Env(tmp_path, key="k", borges_max_active_runs=1, borges_allow_untrusted_local=True)
    stub_upload(env)
    env.orchestrator.active = 1
    body = {**UPLOAD, "decision_rule": {"metric": "effect", "alpha": alpha}}
    response = await post(env, body, uploader(env))
    assert response.status_code == 400
    assert "alpha" in response.json()["detail"]


@pytest.mark.parametrize(
    "rule",
    [
        {"metric": " "},
        {"metric": "m", "positive_label": ""},
        {"metric": "m", "negative_label": " "},
    ],
)
async def test_other_bad_rules_are_400(tmp_path, rule: dict) -> None:
    env = Env(tmp_path, key="k", borges_allow_untrusted_local=True)
    stub_upload(env)
    response = await post(env, {**UPLOAD, "decision_rule": rule}, uploader(env))
    assert response.status_code == 400
    assert "decision rule" in response.json()["detail"]


async def test_upload_without_a_question_is_400_before_the_gates(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_max_active_runs=1, borges_allow_untrusted_local=True)
    stub_upload(env)
    env.orchestrator.active = 1
    body = {k: v for k, v in UPLOAD.items() if k != "question"}
    response = await post(env, body, uploader(env))
    assert response.status_code == 400
    assert "question" in response.json()["detail"]


async def test_registry_gate_comes_after_request_validation(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_registry_enforce=True, borges_allow_untrusted_local=True)
    response = await post(env, UPLOAD, uploader(env))
    assert response.status_code == 400
    assert "Unknown upload" in response.json()["detail"]
