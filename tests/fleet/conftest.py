from __future__ import annotations

from pathlib import Path

import pytest

from borges.config import REPO_ROOT, Settings
from borges.fleet.fleet import Fleet, build_fleet
from borges.fleet.store import RegistryStore


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=REPO_ROOT / "cases",
    )


@pytest.fixture
def fleet(settings: Settings) -> Fleet:
    return build_fleet(settings)


@pytest.fixture
def empty_store(tmp_path: Path) -> RegistryStore:
    return RegistryStore(tmp_path / "registry.jsonl")
