# Security model

Generated code comes from a model or from an upload. Three layers, from weakest to strongest:

1. **AST code guard (first layer, a lint).** Default-deny: no underscore attributes, frame and
   traceback attributes, `type`, `getattr`, `exec`, computed string subscripts, and an exact
   import allowlist. It stops accidents and the bypasses we know of; it is not a sandbox.
2. **Runtime audit-hook policy (defense in depth).** Every step file starts by installing a
   PEP 578 audit hook (`src/borges/analysis/runtime_policy.py`, 219 lines, embedded by
   `harness.render_step` through `harness.policy_prelude`) before any generated code runs. It
   runs inside the step process, the same code on the local backend and on ConTree. A denied
   event raises `PermissionError: runtime policy denied <event>`, with no host path in the
   message.
3. **VM isolation (ConTree).** The same policy runs inside the VM. That path has never run
   live.

## What the runtime policy blocks

- **Process creation** (`subprocess`, `os.system`, `os.exec*`, `os.spawn*`, `posix_spawn`,
  `fork`, `pty.spawn`); **network** (`socket` connect, bind, getaddrinfo, sendto, sendmsg, name
  lookups; `urllib` fails through these); `webbrowser.open`; every `ctypes.*` event and the
  import of `cffi` from non-library code.
- **Writes**, creates, truncates, removes, renames, `mkdir`, links, `chmod` and `shutil` copies
  or moves outside the step's working directory (`/dev/null` excepted); `os.chdir` out of it
  (including `..`); registering a later audit hook. Paths are resolved with `realpath`, so
  symlinks and `..` do not escape.
- **Reads are allowlisted.** Enforced on the audit events `open` (read mode), `os.listdir` and
  `os.scandir`; `glob` reaches the filesystem through those two, so it is covered. A denied
  open raises `PermissionError: runtime policy denied open for reading`, a denied listing
  `runtime policy denied os.listdir` or `... os.scandir`, never with the path. Opens by file
  descriptor and `listdir(None)` are allowed.

### Reads allowed

All roots are resolved with `realpath` at install time and again on every access.

- The step's working directory (the harness data, `data.parquet`, and `state/` live there).
- Python roots: `sys.prefix`, `sys.base_prefix`, `sys.exec_prefix`, `sys.base_exec_prefix`,
  every `sysconfig` path (including the project's `.venv`), and every `sys.path` entry that is
  a directory and is either outside the real home or under those roots. Roots equal to `/` or
  containing the home are dropped.
- System roots: `/usr/lib`, `/usr/share`, `/usr/local/lib`, `/usr/local/share`, `/lib`,
  `/lib64`, `/System/Library`, `/Library/Fonts`, `/opt/homebrew`, `/private/var/db/timezone`,
  `/sys/devices/system/cpu`, `/sys/fs/cgroup`, and `/proc/<own pid>/` (`/proc/self` resolves
  to it).
- Exact files: `/dev/null`, `/dev/urandom`, `/dev/random`, `/proc/cpuinfo`, `/proc/meminfo`,
  `/etc/localtime`, `/etc/timezone`.

### Reads always denied

Checked on both the joined path and the `realpath`, before any allow rule:

- Any file whose final component is `.env` or starts with `.env.`, even inside allowed roots.
- Anything under `/proc` whose path contains the component `environ`, `mem`, `maps`, `smaps`,
  `pagemap` or `mountinfo`.
- `/proc/<pid>/` for any pid other than the process's own. The rule is path based, so
  `/proc/1/environ` is denied on macOS too, where the file does not exist.
- Anything under the real user's home (taken from the pwd database, not `$HOME`, which is the
  step's filesystem) unless it is under the working directory or a Python root.
- Everything else, including `/etc/hosts`, `/etc/passwd` and listing `/`.

`harness.render_step(step, option, policy_home=None, policy_audit_path=None)`: `policy_home`
overrides the real home, for tests; `policy_audit_path` is off by default and, when set,
appends each denied read to that file and allows it (an audit mode for tracing). Generated
code cannot set either.

## Evidence

- The four curated cases run under the enforced policy give the same universes, statuses,
  choices, estimates and p-values (9 decimals) as the committed recordings: `checkout_ab` 7
  universes, 22 checkpoints, SHIP; `red_cards` 30 and 58, BIAS DETECTED; `marp_religiosity`
  40 and 118, POSITIVE ASSOCIATION; `marp_norms` 15 and 67, DEPENDS ON NORMS.
- Audit tracing over those cases found no legitimate denied read (the only one on macOS is the
  listing of the project's own `src`, which the import machinery tolerates); the same on
  Linux in the existing `borges:latest` image for the pandas, numpy, pyarrow, patsy, scipy and
  statsmodels OLS stack. There, `/proc/1/environ`, the process's own `/proc/<pid>/environ`,
  `/proc/self/environ`, `/etc/passwd`, `/app/.env` and `/home/borges/.ssh/id` are denied.
- With the read check forced to allow everything, 17 of the read tests fail, so they fail on
  the old behaviour. Tests: `tests/sandbox/test_runtime_policy.py` and
  `tests/sandbox/test_runtime_policy_reads.py`.
- Overhead: one statsmodels OLS step through `LocalBackend`, median of 10 runs, two alternating
  rounds: 0.886 s and 0.899 s without the policy, 0.973 s and 0.984 s with it, about +0.09 s
  (+10%).

## What the policy does not do

- **The local backend is not an isolation boundary.** The policy is not a VM or a container.
- A native-code exploit in a C extension (numpy, pyarrow) runs below the interpreter and is
  not audited.
- CPU and memory abuse are bounded only by rlimits (CPU 600 s, file size 256 MB, 1024
  processes, and 3072 MB address space on Linux only, not on macOS) and the 120 s step
  timeout; writes inside the working directory can fill disk up to those limits.
- Reads are an allowlist, but anything inside it is readable and could be printed into a
  result or error: the working directory, the Python roots (including every installed package
  and any directory on `sys.path` outside the home) and the system roots above.
- `/proc/self/cgroup` is not allowed (only `/sys/fs/cgroup`); no legitimate read hit that in
  the Docker run.
- A generated `import ctypes` succeeds silently (the module is pre-imported) but every
  `ctypes.*` event is denied, so it can do nothing.
- Audit hooks are defense in depth under the guard: an unaudited primitive in a new CPython
  release would be a gap. Threads and signals are not restricted.
- Proven on the local backend and on the Linux image with a mounted source tree (no image
  rebuild). ConTree remote sandboxes were not exercised: they get the same prelude, and their
  Python prefixes (`/usr/local` or `/usr`) are covered by `sys.prefix` and the system roots.

So: the local backend is for trusted-ish generated code behind the policy and the guard, and
ConTree is the isolated path. Public deployments with live or upload runs should set
`BORGES_BACKEND=contree`.

## Server rules

- **Uploads are refused on the local backend** (`POST /api/runs` with an `upload_id` returns
  400) unless `BORGES_ALLOW_UNTRUSTED_LOCAL` is true, which only `make dev`
  sets. Live runs on a curated case are not refused on the local backend by the server; do not
  expose that combination publicly.
- The server, not the client, picks the backend, clamps `max_universes`, limits concurrency
  (429), refuses live runs without a key (400) or past the spend cap (403), and can require
  `X-Borges-Live-Token` for uploads. The built-in UI does not send that header.
- Never commit `.env`. CI (`.github/workflows/ci.yml`) runs lint, tests and the frontend
  build; a badge will exist once the repository is public.
