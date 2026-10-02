from __future__ import annotations

from borges.analysis import harness
from tests.sandbox.policy_probe import run_probes

GOLDEN = {
    "getframe": "ok",
    "import_ctypes": "ok",
    "import_socket_free": "ok",
    "listdir_cwd": "ok",
    "listdir_root": "PermissionError runtime policy denied os.listdir",
    "mkdir_inside": "ok",
    "mkdir_outside": "PermissionError runtime policy denied os.mkdir",
    "open_env": "PermissionError runtime policy denied open for reading",
    "open_env_local": "PermissionError runtime policy denied open for reading",
    "open_local_file": "ok",
    "os_system": "PermissionError runtime policy denied os.system",
    "proc_environ": "PermissionError runtime policy denied open for reading",
    "read_etc_passwd": "PermissionError runtime policy denied open for reading",
    "read_home": "PermissionError runtime policy denied open for reading",
    "remove_outside": "PermissionError runtime policy denied os.remove",
    "setrlimit_lower": "ok",
    "setrlimit_raise": "ok",
    "setsid": "PermissionError runtime policy denied a call that would reach the policy",
    "signal_signal": "PermissionError runtime policy denied a call that would reach the policy",
    "subprocess_run": "PermissionError runtime policy denied subprocess.Popen",
    "write_local_file": "ok",
    "write_outside": "PermissionError runtime policy denied open for writing",
}


def test_rendered_hook_is_one_installer_call_and_compiles() -> None:
    rendered = harness.policy_prelude("/home/x", "/tmp/audit")
    assert rendered.count("_borges_install_policy(") == 2
    assert "/home/x" in rendered
    assert "/tmp/audit" in rendered
    assert "from borges" not in rendered
    for part in ("_borges_make_access", "_borges_refuse", "_borges_walk", "_BORGES_BLOCKED_EVENTS"):
        assert part in rendered
    compile(rendered, "<hook>", "exec")
    assert harness.POLICY_SOURCE.count("_borges_install_policy(None, None)") == 1


def test_rendered_hook_behaves_as_before_the_split() -> None:
    assert run_probes() == GOLDEN
