from __future__ import annotations

from pathlib import Path

import pytest

from borges.config import REPO_ROOT, Settings
from borges.memory.db import open_memory_db
from borges.memory.repository import MemoryRepository
from borges.memory.seal import Sealer

KEY = "k" * 32


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=REPO_ROOT / "cases",
        borges_memory=True,
        borges_memory_key=KEY,
    )


@pytest.fixture
def repo(tmp_path: Path) -> MemoryRepository:
    return MemoryRepository(open_memory_db(tmp_path / "m.db"), Sealer(KEY))


@pytest.fixture
def plain_repo(tmp_path: Path) -> MemoryRepository:
    return MemoryRepository(open_memory_db(tmp_path / "p.db"), Sealer(None))
