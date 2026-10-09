from __future__ import annotations

import pytest

from borges.analysis.prompts import judge
from borges.config import Settings
from borges.fleet.provenance import run_provenance
from tests.fleet.seed_versions import seed_version


def test_every_agent_is_recorded_with_version_and_sha(settings: Settings) -> None:
    result = run_provenance(settings, "nebius")
    assert len(result.agents) == 12 and len(result.registry_sha) == 64
    judge_use = next(a for a in result.agents if a.agent_id == "judge")
    assert judge_use.version == seed_version("judge") and judge_use.approval == "approved"
    assert judge_use.principal == "agent://borges/judge" and judge_use.prompt_sha


def test_scripted_runs_report_the_scripted_model(settings: Settings) -> None:
    result = run_provenance(settings, "scripted")
    assert next(a for a in result.agents if a.agent_id == "judge").model_id == "scripted"
    assert next(a for a in result.agents if a.agent_id == "harness").model_id == "deterministic"


def test_changed_definition_is_unpublished(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(judge, "SYSTEM", judge.SYSTEM + " Be stricter.")
    use = next(a for a in run_provenance(settings, "scripted").agents if a.agent_id == "judge")
    assert use.version is None and use.approval == "unpublished"
