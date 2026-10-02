from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from borges.llm.client import DEFAULT_ROLE_MODELS, Role
from borges.llm.live_smoke import render_report, run_smoke
from tests.llm.fakes import FakeClient, bad_request, completion

ROOT = Path(__file__).resolve().parents[2]
IDS = sorted({spec.id for spec in DEFAULT_ROLE_MODELS.values()})
OK = '{"ok": true}'


class SmokeClient(FakeClient):
    def __init__(self, listed: list[str], *outcomes: Any) -> None:
        super().__init__(*outcomes)
        data = [SimpleNamespace(id=i) for i in listed]

        async def list_models() -> Any:
            return SimpleNamespace(data=data)

        self.models = SimpleNamespace(list=list_models)


def clean(text: str = OK, **kw: Any) -> SimpleNamespace:
    response = completion(text, **kw)
    response.choices[0].message.reasoning_content = None
    return response


async def test_all_roles_pass_and_are_reported() -> None:
    client = SmokeClient(IDS, *[clean(tokens_in=40, tokens_out=6) for _ in Role])
    report = await run_smoke(client)
    assert report.ok
    assert [r.role for r in report.roles] == [r.value for r in DEFAULT_ROLE_MODELS]
    assert all(r.tokens_in == 40 and r.tokens_out == 6 and r.cost_usd > 0 for r in report.roles)
    assert all(c["max_tokens"] <= 64 for c in client.calls)
    assert all(
        c["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False for c in client.calls
    )
    assert report.total_cost_usd < 0.05
    assert "RESULT: PASS" in render_report(report)[-1]


async def test_missing_model_id_fails() -> None:
    client = SmokeClient(IDS[:2], *[clean() for _ in Role])
    report = await run_smoke(client)
    assert not report.ok
    assert report.missing_models == IDS[2:]


async def test_reasoning_with_thinking_disabled_fails() -> None:
    leaky = completion(OK)
    client = SmokeClient(IDS, leaky, *[clean() for _ in range(4)])
    report = await run_smoke(client)
    assert not report.ok
    assert report.roles[0].reasoning and "thinking disabled" in (report.roles[0].error or "")


async def test_role_error_is_reported_without_aborting() -> None:
    client = SmokeClient(IDS, bad_request("model not found"), *[clean() for _ in range(4)])
    report = await run_smoke(client)
    assert not report.ok
    assert "model not found" in (report.roles[0].error or "")
    assert all(r.ok for r in report.roles[1:])


async def test_cost_cap_stops_further_calls() -> None:
    client = SmokeClient(IDS, *[clean(tokens_in=10**5, tokens_out=10**5) for _ in Role])
    report = await run_smoke(client, cap_usd=0.05)
    assert not report.ok
    assert len(client.calls) < 5
    assert any("cap" in (r.error or "") for r in report.roles)


def test_without_key_exits_with_clear_message(tmp_path: Path) -> None:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "NEBIUS_API_KEY": ""}
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "live_smoke.py")],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    assert result.returncode == 2
    assert "NEBIUS_API_KEY is not set" in result.stderr
