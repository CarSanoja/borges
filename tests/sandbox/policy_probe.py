from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from borges.analysis import harness

RLIM = "(lambda r: r.setrlimit"
PROBES = {
    "open_env": "open('.env').read()",
    "open_env_local": "open('.env.local').read()",
    "open_local_file": "open('data.txt').read()",
    "write_local_file": "open('out.txt', 'w').write('x')",
    "write_outside": "open('/tmp/borges_probe_outside.txt', 'w').write('x')",
    "read_etc_passwd": "open('/etc/passwd').read()",
    "read_home": "open(__import__('os').path.expanduser('~/.zshrc')).read()",
    "proc_environ": "open('/proc/1/environ').read()",
    "import_ctypes": "__import__('ctypes')",
    "import_socket_free": "__import__('json')",
    "listdir_root": "__import__('os').listdir('/')",
    "listdir_cwd": "__import__('os').listdir('.')",
    "setsid": "__import__('os').setsid()",
    "signal_signal": "__import__('signal').signal(__import__('signal').SIGUSR1, lambda *a: 0)",
    "setrlimit_raise": RLIM + "(r.RLIMIT_CORE, (0, 0)) or r.setrlimit(r.RLIMIT_CORE, (0, 1)))"
    "(__import__('resource'))",
    "setrlimit_lower": RLIM + "(r.RLIMIT_CORE, (0, 0)))(__import__('resource'))",
    "getframe": "(lambda: sys._getframe(0))()",
    "subprocess_run": "__import__('subprocess').run(['true'])",
    "os_system": "__import__('os').system('true')",
    "mkdir_inside": "__import__('os').mkdir('probe_dir')",
    "mkdir_outside": "__import__('os').mkdir('/tmp/borges_probe_dir')",
    "remove_outside": "__import__('os').remove('/tmp/borges_probe_missing')",
}


def run_probes() -> dict[str, str]:
    outcomes: dict[str, str] = {}
    prelude = harness.policy_prelude()
    for label, statement in PROBES.items():
        script = (
            f"{prelude}import sys\ntry:\n    {statement}\nexcept BaseException as e:\n"
            "    print(type(e).__name__, str(e)[:60])\nelse:\n    print('ok')\n"
        )
        with tempfile.TemporaryDirectory() as work:
            (Path(work) / "data.txt").write_text("d")
            (Path(work) / ".env").write_text("K=1")
            (Path(work) / ".env.local").write_text("K=1")
            done = subprocess.run(
                [sys.executable, "-c", script], cwd=work, capture_output=True, text=True, timeout=60
            )
        outcomes[label] = (done.stdout.strip().splitlines() or [f"rc={done.returncode}"])[-1]
    return outcomes


if __name__ == "__main__":
    print(json.dumps(run_probes(), indent=1, sort_keys=True))
