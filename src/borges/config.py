from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    nebius_api_key: str | None = None
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    tavily_api_key: str | None = None
    contree_api_key: str | None = None
    contree_base_url: str | None = None

    borges_llm: Literal["nebius", "scripted"] = "scripted"
    borges_backend: Literal["local", "contree"] = "local"
    borges_spend_cap_usd: float = 5.0
    borges_run_cap_usd: float = 0.50
    borges_max_universes: int = 40
    borges_concurrency: int = 6
    borges_home: Path = REPO_ROOT / ".borges"
    borges_runs_dir: Path = REPO_ROOT / "runs"
    borges_cases_dir: Path = REPO_ROOT / "cases"
    borges_frontend_dist: Path = REPO_ROOT / "frontend" / "dist"


def get_settings() -> Settings:
    return Settings()
