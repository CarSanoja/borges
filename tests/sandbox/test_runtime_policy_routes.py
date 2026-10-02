from __future__ import annotations

from pathlib import Path

import pytest

from borges.sandbox.local_backend import LocalBackend
from tests.sandbox.policy_support import run_step

FSPATH_IN_HOOK = """
import shutil
import sys


class Probe:
    seen = False

    def __fspath__(self):
        frame = sys._getframe(0)
        while frame is not None:
            if frame.f_code.co_filename == "<borges-policy>":
                Probe.seen = True
            frame = frame.f_back
        return "harmless"


def apply(df, ctx):
    try:
        shutil.rmtree(Probe(), ignore_errors=True)
    except PermissionError:
        pass
    print("ATTACKER_CODE_RAN_INSIDE_THE_HOOK" if Probe.seen else "clean")
    return df
"""

LSTAT_LIES = """
import os


def apply(df, ctx):
    os.symlink("__OUTSIDE_DIR__", "link")
    os.lstat = lambda *a, **k: os.stat_result((0o100644, 0, 0, 1, 0, 0, 0, 0, 0, 0))
    os.readlink = lambda *a, **k: "elsewhere"
    open("link/pwn.txt", "w").write("PWNED")
    return df
"""

DIR_FD = """
import os
import sysconfig


def apply(df, ctx):
    directory = os.open(sysconfig.get_paths()["purelib"], os.O_RDONLY)
    name = "borges_dirfd_probe.txt"
    fd = os.open(name, os.O_WRONLY | os.O_CREAT, 0o600, dir_fd=directory)
    os.close(fd)
    os.remove(name, dir_fd=directory)
    ctx["escaped"] = 1
    return df
"""


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend(tmp_path / "sandbox")


async def test_attacker_code_is_never_called_from_inside_the_hook(backend: LocalBackend) -> None:
    result, error = await run_step(backend, FSPATH_IN_HOOK)
    assert result.exit_code == 0, (result.stdout, result.stderr, error)
    assert "ATTACKER_CODE_RAN_INSIDE_THE_HOOK" not in result.stdout
    assert "clean" in result.stdout


async def test_patching_lstat_and_readlink_does_not_fool_the_path_check(
    backend: LocalBackend, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    code = LSTAT_LIES.replace("__OUTSIDE_DIR__", str(outside))
    result, error = await run_step(backend, code)
    assert not (outside / "pwn.txt").exists()
    assert result.exit_code != 0
    assert error is not None
    assert "runtime policy denied open for writing" in error


async def test_directory_descriptors_outside_the_working_directory_are_refused(
    backend: LocalBackend,
) -> None:
    result, error = await run_step(backend, DIR_FD)
    assert result.exit_code != 0, (result.stdout, result.stderr)
    assert error is not None
    assert "runtime policy denied open for reading" in error
