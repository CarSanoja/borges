from __future__ import annotations

import sys
from pathlib import Path

import pytest

from borges.config import Settings
from borges.sandbox.factory import make_backend
from borges.sandbox.limits import MB, ResourceLimits, limit_pairs, make_preexec
from borges.sandbox.local_backend import LocalBackend


def test_limit_pairs_on_linux_include_address_space() -> None:
    pairs = dict(limit_pairs(ResourceLimits(memory_mb=100, cpu_s=7, fsize_mb=3, nproc=50), "linux"))
    assert pairs == {
        "RLIMIT_AS": 100 * MB,
        "RLIMIT_CPU": 7,
        "RLIMIT_FSIZE": 3 * MB,
        "RLIMIT_NPROC": 50,
    }


def test_limit_pairs_skip_address_space_on_darwin() -> None:
    names = [name for name, _ in limit_pairs(ResourceLimits(), "darwin")]
    assert "RLIMIT_AS" not in names
    assert {"RLIMIT_CPU", "RLIMIT_FSIZE", "RLIMIT_NPROC"} <= set(names)


def test_preexec_is_absent_off_linux() -> None:
    assert make_preexec(ResourceLimits(), "darwin") is None
    assert make_preexec(ResourceLimits(), "win32") is None


def test_factory_threads_settings_into_the_local_backend(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        borges_home=tmp_path,
        borges_sandbox_memory_mb=111,
        borges_sandbox_cpu_s=22,
        borges_sandbox_fsize_mb=3,
    )
    backend = make_backend(settings)
    assert isinstance(backend, LocalBackend)
    assert backend.limits == ResourceLimits(memory_mb=111, cpu_s=22, fsize_mb=3)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="rlimits are applied on linux")
async def test_cpu_limit_kills_a_busy_loop(tmp_path: Path) -> None:
    backend = LocalBackend(tmp_path, limits=ResourceLimits(memory_mb=2048, cpu_s=1, fsize_mb=1))
    root = await backend.root({})
    result = await backend.run(root, ["python", "-c", "while True: pass"], timeout_s=30)
    assert not result.ok and result.exit_code != 124


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="rlimits are applied on linux")
async def test_file_size_limit_stops_a_large_write(tmp_path: Path) -> None:
    backend = LocalBackend(tmp_path, limits=ResourceLimits(memory_mb=2048, cpu_s=30, fsize_mb=1))
    root = await backend.root({})
    code = "open('big','wb').write(b'x' * (8 * 1024 * 1024))"
    result = await backend.run(root, ["python", "-c", code], timeout_s=30)
    assert not result.ok


def test_preexec_is_built_for_linux() -> None:
    assert callable(make_preexec(ResourceLimits(), "linux"))
