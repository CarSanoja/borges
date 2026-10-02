from __future__ import annotations

import pytest
from pydantic import ValidationError

from borges.config import Settings
from borges.garden.models import Report
from borges.runs.models import RunRequest, RunSnapshot


def settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    for key in ("CONTREE_PROJECT_ID", "NEBIUS_PROJECT_ID"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)


def test_policy_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    s = settings(monkeypatch)
    assert s.borges_allow_untrusted_local is False
    assert s.borges_live_token is None
    assert (s.borges_max_active_runs, s.borges_max_live_runs) == (2, 2)
    assert s.borges_upload_quota_mb == 500
    assert s.borges_step_timeout_s == 120.0
    assert (s.borges_sandbox_memory_mb, s.borges_sandbox_cpu_s) == (3072, 600)
    assert s.borges_sandbox_fsize_mb == 256
    assert s.contree_project_id is None


def test_project_id_prefers_contree_then_nebius(monkeypatch: pytest.MonkeyPatch) -> None:
    assert settings(monkeypatch, NEBIUS_PROJECT_ID="n").sandbox_project_id == "n"
    both = settings(monkeypatch, NEBIUS_PROJECT_ID="n", CONTREE_PROJECT_ID="c")
    assert both.sandbox_project_id == "c"
    blank = settings(monkeypatch, NEBIUS_PROJECT_ID="n", CONTREE_PROJECT_ID="")
    assert blank.sandbox_project_id == "n"


def test_question_max_length() -> None:
    assert RunRequest(case_id="c", question="x" * 1000).question
    with pytest.raises(ValidationError):
        RunRequest(case_id="c", question="x" * 1001)


def test_new_model_fields_default() -> None:
    assert RunSnapshot(run_id="r").llm is None and RunSnapshot(run_id="r").backend is None
    assert Report.model_fields["n_failed"].default == 0
    assert Report.model_fields["failed"].default_factory() == []


def test_otlp_endpoint_comes_from_the_standard_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    assert settings(monkeypatch).otel_exporter_otlp_endpoint is None
    s = settings(monkeypatch, OTEL_EXPORTER_OTLP_ENDPOINT="http://collector:4318")
    assert s.otel_exporter_otlp_endpoint == "http://collector:4318"
    assert settings(monkeypatch, OTEL_EXPORTER_OTLP_ENDPOINT="").otel_exporter_otlp_endpoint is None
