from __future__ import annotations

from pathlib import Path

import pytest

from borges.config import Settings
from borges.sandbox.backend import SandboxError
from borges.sandbox.factory import make_backend
from borges.sandbox.local_backend import LocalBackend


def _settings(tmp_path: Path, **kwargs: object) -> Settings:
    return Settings(_env_file=None, borges_home=tmp_path, **kwargs)  # type: ignore[call-arg]


def test_local_is_default(tmp_path: Path) -> None:
    backend = make_backend(_settings(tmp_path))
    assert isinstance(backend, LocalBackend)
    assert backend.home == tmp_path


def test_contree_requires_key(tmp_path: Path) -> None:
    settings = _settings(tmp_path, contree_base_url="https://example.invalid")
    with pytest.raises(SandboxError, match="API key"):
        make_backend(settings, "contree")


def test_contree_requires_base_url(tmp_path: Path) -> None:
    with pytest.raises(SandboxError, match="CONTREE_BASE_URL"):
        make_backend(_settings(tmp_path, contree_api_key="k"), "contree")


def test_contree_falls_back_to_nebius_key(tmp_path: Path) -> None:
    settings = _settings(tmp_path, nebius_api_key="k", contree_base_url="https://example.invalid")
    backend = make_backend(settings, "contree")
    assert backend.name == "contree"


def test_kind_overrides_setting(tmp_path: Path) -> None:
    settings = _settings(tmp_path, borges_backend="contree")
    assert isinstance(make_backend(settings, "local"), LocalBackend)
