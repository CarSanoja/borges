from __future__ import annotations

from pathlib import Path

import pytest

KEY_ENV = (
    "BORGES_STORE_KEY",
    "BORGES_AUDIT_ANCHOR_KEY",
    "BORGES_MEMORY_KEY",
    "BORGES_STORE_KEY_AUTOGEN",
)


@pytest.fixture(autouse=True)
def isolated_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    for name in KEY_ENV:
        monkeypatch.setenv(name, "")
        monkeypatch.delenv(name)
    home: Path = tmp_path_factory.mktemp("borges-home")
    monkeypatch.setenv("BORGES_HOME", str(home))
