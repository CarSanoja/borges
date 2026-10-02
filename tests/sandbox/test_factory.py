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
    assert backend.home.parent == tmp_path / "sandboxes"
    assert backend.ephemeral


async def test_each_local_backend_owns_a_directory_removed_on_close(tmp_path: Path) -> None:
    first = make_backend(_settings(tmp_path))
    second = make_backend(_settings(tmp_path))
    assert isinstance(first, LocalBackend) and isinstance(second, LocalBackend)
    assert first.home != second.home
    await first.root({"data.parquet": b"x"})
    await second.root({"data.parquet": b"y"})
    await first.close()
    assert not first.home.exists()
    assert second.home.exists()


def test_contree_requires_key(tmp_path: Path) -> None:
    settings = _settings(tmp_path, contree_project_id="proj-9")
    with pytest.raises(SandboxError, match="API key"):
        make_backend(settings, "contree")


def test_contree_requires_project_id(tmp_path: Path) -> None:
    with pytest.raises(SandboxError, match="NEBIUS_PROJECT_ID"):
        make_backend(_settings(tmp_path, contree_api_key="k"), "contree")


def test_contree_defaults_to_token_factory_sandboxes(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    assert settings.contree_base_url == "https://api.tokenfactory.nebius.com/sandboxes/"


def test_empty_env_values_keep_the_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONTREE_BASE_URL", "")
    monkeypatch.setenv("CONTREE_PROJECT_ID", "")
    monkeypatch.setenv("NEBIUS_PROJECT_ID", "proj-9")
    settings = _settings(tmp_path, contree_api_key="k")
    assert settings.contree_base_url == "https://api.tokenfactory.nebius.com/sandboxes/"
    backend = make_backend(settings, "contree")
    assert backend._client.config.auth.get_headers()["Project"] == "proj-9"


def test_contree_falls_back_to_nebius_key(tmp_path: Path) -> None:
    settings = _settings(tmp_path, nebius_api_key="k", contree_project_id="proj-9")
    backend = make_backend(settings, "contree")
    assert backend.name == "contree"


def test_kind_overrides_setting(tmp_path: Path) -> None:
    settings = _settings(tmp_path, borges_backend="contree")
    assert isinstance(make_backend(settings, "local"), LocalBackend)


def test_contree_project_id_comes_from_settings(tmp_path: Path) -> None:
    settings = _settings(tmp_path, contree_api_key="k", contree_project_id="proj-9")
    backend = make_backend(settings, "contree")
    assert backend._client.config.auth.get_headers()["Project"] == "proj-9"
