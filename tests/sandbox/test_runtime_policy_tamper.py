from __future__ import annotations

from pathlib import Path

import pytest

from borges.sandbox.local_backend import LocalBackend
from tests.sandbox.policy_support import assert_tamper_stopped, run_step

GC_CLOSURE = """
import gc
import os
import types


def apply(df, ctx):
    for obj in gc.get_objects():
        if type(obj) is types.FunctionType and obj.__name__ == "hook" and obj.__closure__:
            for cell in obj.__closure__:
                try:
                    if isinstance(cell.cell_contents, frozenset):
                        cell.cell_contents = frozenset()
                except ValueError:
                    pass
    os.system("echo PWNED > __OUTSIDE__")
    return df
"""

PATCH_BUILTIN = """
import builtins


def apply(df, ctx):
    builtins.isinstance = lambda *a, **k: True
    open("__OUTSIDE__", "w").write("PWNED")
    return df
"""

SHADOW_GLOBAL = """
isinstance = lambda *a, **k: True


def apply(df, ctx):
    open("__OUTSIDE__", "w").write("PWNED")
    return df
"""


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend(tmp_path / "sandbox")


async def test_gc_closure_exploit_cannot_swap_the_blocked_set(
    backend: LocalBackend, tmp_path: Path
) -> None:
    await assert_tamper_stopped(backend, tmp_path, GC_CLOSURE, "gc.get_objects")


@pytest.mark.parametrize(
    ("statement", "event"),
    [
        ("import gc; gc.get_objects()", "gc.get_objects"),
        ("import gc; gc.get_referrers(os)", "gc.get_referrers"),
        ("import gc; gc.get_referents(os.__dict__)", "gc.get_referents"),
        ("import sys; sys._current_frames()", "sys._current_frames"),
    ],
)
async def test_object_graph_and_frame_enumeration_are_denied(
    backend: LocalBackend, statement: str, event: str
) -> None:
    code = f"import os\n\n\ndef apply(df, ctx):\n    {statement}\n    return df\n"
    result, error = await run_step(backend, code)
    assert result.exit_code != 0
    assert error is not None
    assert f"runtime policy denied {event}" in error


@pytest.mark.parametrize(
    "template",
    [pytest.param(PATCH_BUILTIN, id="builtins"), pytest.param(SHADOW_GLOBAL, id="shadow")],
)
async def test_patched_builtins_do_not_reach_the_hook(
    backend: LocalBackend, tmp_path: Path, template: str
) -> None:
    await assert_tamper_stopped(backend, tmp_path, template, "")
