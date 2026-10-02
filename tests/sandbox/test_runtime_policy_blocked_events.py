from __future__ import annotations

import resource
from pathlib import Path

import pytest

from borges.analysis.runtime_policy_config import _BORGES_BLOCKED_EVENTS
from borges.sandbox.local_backend import LocalBackend
from tests.sandbox.policy_support import run_step

ATTEMPTS = {
    "subprocess.Popen": "import subprocess; subprocess.Popen(['true'])",
    "os.system": "os.system('true')",
    "os.exec": "os.execv('/bin/true', ['true'])",
    "os.posix_spawn": "os.posix_spawn('/bin/true', ['true'], {})",
    "os.fork": "os.fork()",
    "os.forkpty": "os.forkpty()",
    "pty.spawn": "import pty; pty.spawn(['true'])",
    "webbrowser.open": "import webbrowser; webbrowser.open('http://127.0.0.1:9')",
    "socket.connect": "import socket; socket.socket().connect(('127.0.0.1', 9))",
    "socket.bind": "import socket; socket.socket().bind(('127.0.0.1', 0))",
    "socket.getaddrinfo": "import socket; socket.getaddrinfo('example.com', 80)",
    "socket.sendto": (
        "import socket; socket.socket(type=socket.SOCK_DGRAM).sendto(b'x', ('127.0.0.1', 9))"
    ),
    "socket.sendmsg": (
        "import socket; "
        "socket.socket(type=socket.SOCK_DGRAM).sendmsg([b'x'], [], 0, ('127.0.0.1', 9))"
    ),
    "socket.gethostbyname": "import socket; socket.gethostbyname('example.com')",
    "socket.gethostbyaddr": "import socket; socket.gethostbyaddr('127.0.0.1')",
    "socket.getnameinfo": "import socket; socket.getnameinfo(('127.0.0.1', 80), 0)",
    "socket.getservbyname": "import socket; socket.getservbyname('http')",
    "socket.getservbyport": "import socket; socket.getservbyport(80)",
    "gc.get_objects": "import gc; gc.get_objects()",
    "gc.get_referrers": "import gc; gc.get_referrers(os)",
    "gc.get_referents": "import gc; gc.get_referents(os)",
    "sys._current_frames": "import sys; sys._current_frames()",
    "sys.settrace": "import sys; sys.settrace(lambda *a: None)",
    "sys.setprofile": "import sys; sys.setprofile(lambda *a: None)",
    "os.kill": "os.kill(os.getpid(), 0)",
    "os.killpg": "os.killpg(os.getpgrp(), 0)",
    "signal.pthread_kill": (
        "import signal, threading; signal.pthread_kill(threading.get_ident(), 0)"
    ),
    "resource.prlimit": "import resource; resource.prlimit(0, resource.RLIMIT_CPU)",
}

ACCEPTED_ELSEWHERE = {"sys.addaudithook": "test_runtime_policy.py"}


def body(statement: str) -> str:
    return f"import os\n\n\ndef apply(df, ctx):\n    {statement}\n    return df\n"


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend(tmp_path / "sandbox")


def test_every_blocked_event_has_an_attempt() -> None:
    covered = set(ATTEMPTS) | set(ACCEPTED_ELSEWHERE)
    assert covered == _BORGES_BLOCKED_EVENTS


@pytest.mark.parametrize("event", sorted(ATTEMPTS))
async def test_blocked_event_is_denied_when_attempted(backend: LocalBackend, event: str) -> None:
    if event == "resource.prlimit" and not hasattr(resource, "prlimit"):
        pytest.skip("resource.prlimit exists on Linux only")
    result, error = await run_step(backend, body(ATTEMPTS[event]))
    assert result.exit_code != 0
    assert error is not None
    assert f"runtime policy denied {event}" in error
