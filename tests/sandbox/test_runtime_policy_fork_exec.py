from __future__ import annotations

from pathlib import Path

import pytest

from borges.sandbox.local_backend import LocalBackend
from tests.sandbox.policy_support import run_step

ARGS = (
    '["touch", "__OUTSIDE__"], [b"/usr/bin/touch"], True, (), None, None, '
    "-1, -1, -1, -1, -1, -1, r, w, False, False, -1, -1, None, -1, -1, None, False"
)

FORK_EXEC = """
import _posixsubprocess
import os


def apply(df, ctx):
    read_fd, write_fd = os.pipe()
    _posixsubprocess.fork_exec(
        ["touch", "__OUTSIDE__"], [b"/usr/bin/touch"], True, (), None, None,
        -1, -1, -1, -1, -1, -1, read_fd, write_fd, False, False, -1, -1, None, -1, -1, None, False,
    )
    return df
"""

ROUTES = {
    "pop_and_reimport": (
        "import sys\nsys.modules.pop('_posixsubprocess')\nimport _posixsubprocess as m"
    ),
    "importlib_reload": (
        "import importlib, _posixsubprocess\nm = importlib.reload(_posixsubprocess)"
    ),
    "import_module_after_pop": (
        "import sys, importlib\nsys.modules.pop('_posixsubprocess')\n"
        "m = importlib.import_module('_posixsubprocess')"
    ),
    "extension_file_loader": (
        "import importlib.util, _posixsubprocess\n"
        "spec = importlib.util.spec_from_file_location("
        "'_posixsubprocess', _posixsubprocess.__spec__.origin)\n"
        "m = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(m)"
    ),
    "imp_create_dynamic": (
        "import _imp, _posixsubprocess\nm = _imp.create_dynamic(_posixsubprocess.__spec__)"
    ),
    "reload_subprocess": (
        "import importlib, subprocess\nimportlib.reload(subprocess)\nm = subprocess\n"
        "m.fork_exec = m._fork_exec"
    ),
}


def route_code(route: str) -> str:
    return (
        "import os\n\n\ndef apply(df, ctx):\n"
        "    r, w = os.pipe()\n"
        + "".join(f"    {line}\n" for line in route.splitlines())
        + f"    m.fork_exec({ARGS})\n    return df\n"
    )


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend(tmp_path / "sandbox")


async def test_fork_exec_cannot_spawn_a_process(backend: LocalBackend, tmp_path: Path) -> None:
    outside = tmp_path / "forked.txt"
    result, error = await run_step(backend, FORK_EXEC.replace("__OUTSIDE__", str(outside)))
    assert not outside.exists()
    assert result.exit_code != 0
    assert error is not None
    assert "runtime policy denied" in error


@pytest.mark.parametrize("route", list(ROUTES))
async def test_routes_back_to_the_original_fork_exec_are_closed(
    backend: LocalBackend, tmp_path: Path, route: str
) -> None:
    outside = tmp_path / "forked.txt"
    code = route_code(ROUTES[route]).replace("__OUTSIDE__", str(outside))
    result, error = await run_step(backend, code)
    assert not outside.exists()
    assert result.exit_code != 0
    assert error is not None
    assert "runtime policy denied" in error
