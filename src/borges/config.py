from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTREE_URL = "https://api.tokenfactory.nebius.com/sandboxes/"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    nebius_api_key: str | None = None
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    tavily_api_key: str | None = None
    contree_api_key: str | None = None
    contree_base_url: str = CONTREE_URL

    contree_project_id: str | None = None
    nebius_project_id: str | None = None

    @field_validator("contree_base_url", mode="before")
    @classmethod
    def _contree_url_or_default(cls, value: object) -> object:
        return value or CONTREE_URL

    @field_validator("otel_exporter_otlp_endpoint", mode="before")
    @classmethod
    def _blank_endpoint_is_unset(cls, value: object) -> object:
        return value or None

    @property
    def sandbox_project_id(self) -> str | None:
        return self.contree_project_id or self.nebius_project_id

    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "borges"

    borges_local_base_url: str = "http://localhost:11434/v1"
    borges_local_model: str = "nemotron-3-nano:30b"
    borges_llm: Literal["nebius", "scripted"] = "scripted"
    borges_backend: Literal["local", "contree"] = "local"
    borges_spend_cap_usd: float = 5.0
    borges_run_cap_usd: float = 0.50
    borges_max_universes: int = 40
    borges_concurrency: int = 6
    borges_allow_untrusted_local: bool = False
    borges_live_token: str | None = None
    borges_max_active_runs: int = 2
    borges_max_live_runs: int = 2
    borges_upload_quota_mb: int = 500
    borges_step_timeout_s: float = 120.0
    borges_sandbox_memory_mb: int = 3072
    borges_sandbox_cpu_s: int = 600
    borges_sandbox_fsize_mb: int = 256
    borges_registry_enforce: bool = False
    borges_registry_four_eyes: bool = False
    borges_rate_anon_burst: int = 120
    borges_rate_anon_per_s: float = 5.0
    borges_rate_key_burst: int = 400
    borges_rate_key_per_s: float = 30.0
    borges_audit_reads: bool = False
    borges_anon_active_runs: int = 1
    borges_anon_runs_per_min: float = 6.0
    borges_anon_live_runs_per_hour: float = 12.0
    borges_agent_token_ttl_s: int = 3600
    borges_audit_anchor_key: str | None = None
    borges_audit_anchor_every: int = 50
    borges_store_key: str | None = None
    borges_store_key_autogen: bool = False
    borges_armor_llm: bool = False
    borges_memory: bool = False
    borges_memory_key: str | None = None
    borges_memory_similarity: float = 0.9
    borges_job_lease_s: float = 30.0
    borges_job_max_attempts: int = 3
    borges_job_backoff_s: float = 2.0
    borges_runtime_poll_s: float = 1.0
    borges_idempotency_window_s: float = 600.0
    borges_scheduler: bool = False
    borges_scheduler_poll_s: float = 30.0
    borges_gateway_policy: Path = REPO_ROOT / "policy" / "gateway.json"
    borges_home: Path = REPO_ROOT / ".borges"
    borges_runs_dir: Path = REPO_ROOT / "runs"
    borges_cases_dir: Path = REPO_ROOT / "cases"
    borges_frontend_dist: Path = REPO_ROOT / "frontend" / "dist"


def get_settings() -> Settings:
    return Settings()
