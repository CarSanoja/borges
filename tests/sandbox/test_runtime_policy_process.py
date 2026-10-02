from __future__ import annotations

from pathlib import Path

import pytest

from borges.sandbox.local_backend import LocalBackend
from tests.sandbox.policy_support import run_step

REACH = "a call that would reach the policy"


def body(statement: str) -> str:
    return f"import os\n\n\ndef apply(df, ctx):\n    {statement}\n    return df\n"


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend(tmp_path / "sandbox")


@pytest.mark.parametrize(
    ("statement", "denial"),
    [
        ("os.kill(os.getppid(), 0)", "os.kill"),
        ("os.kill(os.getpid(), 0)", "os.kill"),
        ("os.killpg(os.getpgrp(), 0)", "os.killpg"),
        (
            "import signal, threading; signal.pthread_kill(threading.get_ident(), 0)",
            "signal.pthread_kill",
        ),
        ("import sys; sys.settrace(lambda *a: None)", "sys.settrace"),
        ("import sys; sys.setprofile(lambda *a: None)", "sys.setprofile"),
    ],
)
async def test_signals_and_tracing_are_denied_by_event(
    backend: LocalBackend, statement: str, denial: str
) -> None:
    result, error = await run_step(backend, body(statement))
    assert result.exit_code != 0
    assert error is not None
    assert f"runtime policy denied {denial}" in error


async def test_trace_functions_cannot_be_installed_in_new_threads(backend: LocalBackend) -> None:
    statement = (
        "import threading; threading.settrace(lambda *a: None); "
        "t = threading.Thread(target=int); t.start(); t.join()"
    )
    result, _ = await run_step(backend, body(statement))
    assert "runtime policy denied sys.settrace" in result.stderr


@pytest.mark.parametrize(
    "statement",
    [
        "import signal; signal.signal(signal.SIGUSR1, lambda *a: None)",
        "import _signal; _signal.signal(10, lambda *a: None)",
        "import signal; signal.setitimer(signal.ITIMER_REAL, 0.01)",
        "import signal; signal.alarm(1)",
        "os.setsid()",
        "os.setpgid(0, 0)",
        "import posix; posix.setsid()",
        "import sys; sys.monitoring.use_tool_id(3, 'x')",
        "import sys; sys.monitoring.register_callback(3, 1, lambda *a: None)",
        "import sys; sys.monitoring.set_events(3, 1)",
    ],
)
async def test_handlers_sessions_and_monitoring_are_refused(
    backend: LocalBackend, statement: str
) -> None:
    result, error = await run_step(backend, body(statement))
    assert result.exit_code != 0
    assert error is not None
    assert REACH in error


RAISE_LIMIT = (
    "import resource; soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE); "
    "resource.setrlimit(resource.RLIMIT_NOFILE, (soft // 2, hard)); "
    "resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))"
)
RAISE_HARD = (
    "import resource; soft, hard = resource.getrlimit(resource.RLIMIT_CORE); "
    "resource.setrlimit(resource.RLIMIT_CORE, (0, 0)); "
    "resource.setrlimit(resource.RLIMIT_CORE, (0, 1))"
)


@pytest.mark.parametrize("statement", [RAISE_LIMIT, RAISE_HARD])
async def test_rlimits_cannot_be_raised(backend: LocalBackend, statement: str) -> None:
    result, error = await run_step(backend, body(statement))
    assert result.exit_code != 0
    assert error is not None
    assert "runtime policy denied resource.setrlimit" in error


async def test_rlimits_can_still_be_lowered(backend: LocalBackend) -> None:
    statement = (
        "import resource; soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE); "
        "resource.setrlimit(resource.RLIMIT_NOFILE, (soft // 2, hard)); "
        "resource.setrlimit(resource.RLIMIT_NOFILE, (soft // 4, soft // 2)); "
        "resource.setrlimit(resource.RLIMIT_CORE, (0, 0))"
    )
    result, error = await run_step(backend, body(statement))
    assert result.exit_code == 0, (result.stdout, result.stderr, error)
