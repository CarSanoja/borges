from __future__ import annotations

from pathlib import Path

import pytest

from borges.sandbox.local_backend import LocalBackend
from tests.sandbox.policy_support import assert_tamper_stopped

TRACEBACK_PRELUDE = """
import os
import types


def policy_frames():
    try:
        os.system("true")
    except PermissionError as exc:
        found = []
        tb = exc.__traceback__
        while tb is not None:
            if tb.tb_frame.f_code.co_filename == "<borges-policy>":
                found.append(tb.tb_frame)
            tb = tb.tb_next
        return found
    return []


def policy_functions():
    found = []
    for frame in policy_frames():
        for value in list(frame.f_locals.values()):
            if type(value) is types.FunctionType:
                found.append(value)
    return found
"""

WRITE_THROUGH = (
    TRACEBACK_PRELUDE
    + """

def apply(df, ctx):
    for frame in policy_frames():
        for key, value in list(frame.f_locals.items()):
            if isinstance(value, frozenset):
                frame.f_locals[key] = frozenset()
    os.system("echo PWNED > __OUTSIDE__")
    return df
"""
)

SWAP_CODE = (
    TRACEBACK_PRELUDE
    + """

def apply(df, ctx):
    noop = (lambda *a, **k: None).__code__
    functions = policy_functions()
    assert functions
    for fn in functions:
        fn.__code__ = noop
    os.system("echo PWNED > __OUTSIDE__")
    return df
"""
)

SWAP_DEFAULTS = (
    TRACEBACK_PRELUDE
    + """

def apply(df, ctx):
    functions = policy_functions()
    assert functions
    for fn in functions:
        fn.__defaults__ = (None,)
    os.system("echo PWNED > __OUTSIDE__")
    return df
"""
)

SWAP_KWDEFAULTS = (
    TRACEBACK_PRELUDE
    + """

def apply(df, ctx):
    functions = policy_functions()
    assert functions
    for fn in functions:
        fn.__kwdefaults__ = {}
    os.system("echo PWNED > __OUTSIDE__")
    return df
"""
)

DELETE_DEFAULTS = (
    TRACEBACK_PRELUDE
    + """

def apply(df, ctx):
    functions = policy_functions()
    assert functions
    for fn in functions:
        del fn.__defaults__
    os.system("echo PWNED > __OUTSIDE__")
    return df
"""
)

CLEAR_GLOBALS = (
    TRACEBACK_PRELUDE
    + """

def apply(df, ctx):
    for fn in policy_functions():
        fn.__globals__.clear()
        fn.__globals__["__builtins__"] = {}
    os.system("echo PWNED > __OUTSIDE__")
    return df
"""
)


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend(tmp_path / "sandbox")


@pytest.mark.parametrize(
    ("template", "denial"),
    [
        pytest.param(WRITE_THROUGH, "os.system", id="write-through"),
        pytest.param(SWAP_CODE, "object.__setattr__ __code__", id="code"),
        pytest.param(SWAP_DEFAULTS, "object.__setattr__ __defaults__", id="defaults"),
        pytest.param(SWAP_KWDEFAULTS, "object.__setattr__ __kwdefaults__", id="kwdefaults"),
        pytest.param(DELETE_DEFAULTS, "object.__delattr__ __defaults__", id="del-defaults"),
        pytest.param(CLEAR_GLOBALS, "os.system", id="globals"),
    ],
)
async def test_policy_state_reached_through_a_traceback_cannot_be_changed(
    backend: LocalBackend, tmp_path: Path, template: str, denial: str
) -> None:
    await assert_tamper_stopped(backend, tmp_path, template, denial)
