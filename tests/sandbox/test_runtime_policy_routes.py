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

SUBINTERPRETER = """
import os


def apply(df, ctx):
    __CREATE__
    m.run_string(m.create(), "import os; os.system('touch __OUTSIDE__')")
    return df
"""

CREATES = {
    "import_statement": "import _interpreters as m",
    "import_module": "import importlib\n    m = importlib.import_module('_interpreters')",
    "create_builtin": (
        "import _imp, importlib.machinery\n"
        "    m = _imp.create_builtin("
        "importlib.machinery.ModuleSpec('_interpreters', None, origin='built-in'))"
    ),
}

ALLOWED_BUILTIN = """
import _imp
import importlib.machinery


def apply(df, ctx):
    spec = importlib.machinery.ModuleSpec("_symtable", None, origin="built-in")
    if _imp.create_builtin(spec) is None:
        raise RuntimeError("an allowed builtin module could not be created")
    return df
"""

TAMPER = """
import _imp


def apply(df, ctx):
    _imp.create_builtin.__defaults__ = (None, list)
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


@pytest.mark.parametrize("route", list(CREATES))
async def test_a_sub_interpreter_cannot_be_created(
    backend: LocalBackend, tmp_path: Path, route: str
) -> None:
    """Code in a sub-interpreter runs outside the audit hook; on Linux builds _interpreters is
    compiled into the interpreter, and importlib.import_module created it with no audit event."""
    outside = tmp_path / "escaped.txt"
    code = SUBINTERPRETER.replace("__CREATE__", CREATES[route])
    result, error = await run_step(backend, code.replace("__OUTSIDE__", str(outside)))
    assert not outside.exists()
    assert result.exit_code != 0
    assert error is not None and "runtime policy denied" in error


@pytest.mark.parametrize("module", ["_testinternalcapi", "_interpchannels"])
async def test_the_interpreter_internals_cannot_be_imported(
    backend: LocalBackend, module: str
) -> None:
    code = f"import importlib\n\n\ndef apply(df, ctx):\n    importlib.import_module({module!r})\n"
    result, error = await run_step(backend, code + "    return df\n")
    assert result.exit_code != 0
    assert error is not None and "runtime policy denied" in error


async def test_an_allowed_builtin_module_is_still_created(backend: LocalBackend) -> None:
    result, error = await run_step(backend, ALLOWED_BUILTIN)
    assert result.exit_code == 0, error


async def test_the_guard_on_builtin_creation_cannot_be_rewired(backend: LocalBackend) -> None:
    result, error = await run_step(backend, TAMPER)
    assert result.exit_code != 0
    assert error is not None and "runtime policy denied" in error
