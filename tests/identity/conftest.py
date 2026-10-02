from __future__ import annotations

from pathlib import Path

import pytest

from borges.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None, borges_home=tmp_path / "home", borges_runs_dir=tmp_path / "runs"
    )
