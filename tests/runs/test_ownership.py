from __future__ import annotations

import os
import socket
import subprocess
import sys

from borges.runs.ownership import UNOWNED_CUTOFF_S, is_orphan, owner_fields, pid_alive


def dead_pid() -> int:
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    return process.pid


def test_owner_fields_name_this_process_and_host() -> None:
    fields = owner_fields()
    assert fields == {"owner_pid": os.getpid(), "owner_host": socket.gethostname()}


def test_pid_alive() -> None:
    assert pid_alive(os.getpid())
    assert not pid_alive(dead_pid())


def test_live_owner_is_never_an_orphan_however_old_the_log() -> None:
    meta = owner_fields()
    assert not is_orphan(meta, last_activity=1.0)


def test_dead_owner_is_an_orphan_even_with_a_fresh_log() -> None:
    meta = {"owner_pid": dead_pid(), "owner_host": socket.gethostname()}
    assert is_orphan(meta, last_activity=100.0, now=101.0)


def test_unowned_run_uses_the_cutoff() -> None:
    assert not is_orphan({}, last_activity=1000.0, now=1000.0 + UNOWNED_CUTOFF_S - 1)
    assert is_orphan({}, last_activity=1000.0, now=1000.0 + UNOWNED_CUTOFF_S + 1)


def test_owner_on_another_host_uses_the_cutoff() -> None:
    meta = {"owner_pid": os.getpid(), "owner_host": "elsewhere.invalid"}
    assert not is_orphan(meta, last_activity=1000.0, now=1001.0)
    assert is_orphan(meta, last_activity=1000.0, now=1000.0 + UNOWNED_CUTOFF_S + 1)
