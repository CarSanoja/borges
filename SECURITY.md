# Security model

Generated code comes from a model or from an upload. Read this first: **nothing in this
repository is a security boundary for untrusted code on the local backend.** The runtime policy
is an in-process PEP 578 audit hook, which makes it defense in depth, not a boundary. A
determined attacker with arbitrary Python in the same process may find another route (the ones
we know are open are listed below). That is why untrusted code (uploads, public live runs) must
run on ConTree or in a container, and why `make serve` refuses local uploads (see Server rules).

Three layers, from weakest to strongest:

1. **AST code guard (first layer, a lint).** Default-deny: no underscore attributes, frame and
   traceback attributes, `type`, `getattr`, `exec`, computed string subscripts, and an exact
   import allowlist. It stops accidents and the bypasses we know of; it is not a sandbox.
2. **Runtime audit-hook policy (defense in depth).** Every step file starts by installing a
   PEP 578 audit hook before any generated code runs. The sources are
   `src/borges/analysis/runtime_policy_paths.py`, `runtime_policy_config.py` and
   `runtime_policy.py`, concatenated by `harness.policy_prelude` and run in a fresh globals
   dict. It runs inside the step process, the same code on the local backend and on ConTree. A
   denied event raises `PermissionError: runtime policy denied <event>`, with no host path in
   the message.
3. **VM isolation (ConTree).** The same policy runs inside the VM. That path has never run
   live.

## Why the hook cannot be reached by name

The round 4 jury broke the previous design without the static guard: `gc.get_objects()` found
the hook function, the closure cell holding the blocked set was overwritten, and `os.system`
then wrote a file outside the step directory. The exact exploit is
`test_gc_closure_exploit_cannot_swap_the_blocked_set`; on the previous policy it creates the
file. The hook is now built so that there is nothing to swap:

- No function of the policy has a closure, a global name or a keyword default. Every name it
  uses, builtins included, is bound as a positional default whose value is a C builtin, a
  frozenset, a string, a tuple or another such function. A test disassembles the whole call
  graph and fails on `LOAD_GLOBAL`, `LOAD_NAME`, cell and import opcodes
  (`test_policy_functions_hold_no_cells_globals_or_keyword_defaults`). Patching `builtins`,
  shadowing a name in the step module or clearing `fn.__globals__` changes nothing.
- The hook is defensive: any exception other than the denial itself becomes
  `PermissionError: runtime policy denied internal error`.
- Paths are resolved by the policy's own `lstat`/`readlink` walk using C builtins bound at
  install time, not by `os.path.realpath`, so replacing `os.lstat` or `os.readlink` does not
  fool it. Only exact `str` and `bytes` paths are understood; any other object (a path-like with
  a hostile `__fspath__`) is denied, so no user code is ever called from inside the hook.
- `ctypes` is imported once before the hook is installed, and `cffi` stays blocked. The old
  "import allowed when the importer is library code" rule needed `sys._getframe` inside the
  hook and is gone; every `ctypes.*` event is denied anyway.

## Routes closed and tested

Each row has a regression test. 35 of the 38 new tests fail on the previous policy; the other
three keep working behaviour (an OLS with warnings, lowering limits) or read the current source
(the structure test).

| Route | How it is stopped | Test file |
| --- | --- | --- |
| `gc.get_objects`, `gc.get_referrers`, `gc.get_referents`, `sys._current_frames` | denied audit events | `test_runtime_policy_tamper.py` |
| Hook frames reached from a caught traceback: `f_locals` write-through (Python 3.13 writes free-variable cells), `fn.__code__`, `__defaults__`, `__kwdefaults__`, `del fn.__defaults__`, clearing `fn.__globals__` | no cells or globals to write; `object.__setattr__` and `object.__delattr__` of those attributes on policy functions are denied | `test_runtime_policy_traceback.py` |
| Patching `builtins.isinstance`, shadowing `isinstance` in the step module | the hook uses neither | `test_runtime_policy_tamper.py` |
| Replacing `os.lstat` / `os.readlink` to hide a symlink that points outside | own symlink walk with bound builtins | `test_runtime_policy_routes.py` |
| A path-like whose `__fspath__` runs inside the hook (`shutil.rmtree(obj)`) | non-`str`/`bytes` objects are denied, never converted | `test_runtime_policy_routes.py` |
| `os.open(<dir outside>)` then `os.open(name, dir_fd=...)` to write elsewhere | opening a directory outside the working directory is denied | `test_runtime_policy_routes.py` |
| `os.kill` (including `os.kill(os.getppid(), 0)`), `os.killpg`, `signal.pthread_kill` | denied audit events | `test_runtime_policy_process.py` |
| `signal.signal`, `_signal.signal`, `setitimer`, `alarm`, `set_wakeup_fd` (a handler receives the interrupted frame, possibly a hook frame) | replaced by a refusal in `signal` and `_signal` | `test_runtime_policy_process.py` |
| `sys.settrace`, `sys.setprofile`, trace functions for new threads | denied audit events | `test_runtime_policy_process.py` |
| `sys.monitoring` `use_tool_id`, `set_events`, `set_local_events`, `register_callback` | replaced by a refusal | `test_runtime_policy_process.py` |
| `os.setsid`, `os.setpgid`, `os.setpgrp` (leaving the process group the backend kills on timeout) | replaced by a refusal in `os` and `posix` | `test_runtime_policy_process.py` |
| `resource.setrlimit` raising a soft or hard limit, `resource.prlimit` | raising is denied, lowering still works | `test_runtime_policy_process.py` |

`sys._getframe` is deliberately not denied outside the hook: pandas' `find_stack_level` needs
it, and the pandas, numpy, scipy, statsmodels, patsy and pyarrow stack still runs an OLS with
warnings under the policy (`test_runtime_policy_stack.py`). Inside the hook, re-entrant
`sys._getframe`, `tb_frame`, `gi_frame`, `f_code` and `__code__` reads are denied, which is
partial (next section).

## Routes known to be open

- **Frames of a running hook.** CPython does not audit `coroutine.cr_frame` or `frame.f_back`.
  A finalizer that runs while the hook is being entered or left can walk
  `coroutine.cr_frame.f_back` up to a live hook frame. Measured, not closed: with
  `gc.set_threshold(1, 1, 1)` and 300 rounds of cyclic garbage with `__del__`, 1198 handles to a
  frame named `hook` were obtained (the re-entry denial stops the reads made while the hook is
  running, not the ones in its first and last instructions). A second experiment that rewrote
  the local `event` of that frame so `os.system` would pass did not succeed in 2000 tries, so no
  escape is demonstrated, but the window exists.
- **Time-of-check races.** A symlink swapped between the check and the `open`, or another
  thread changing the file system, is not defended. The re-entry detection counts depth for the
  whole process, not per thread.
- **Unaudited primitives.** `signal.pthread_sigmask`, `os.nice`, `os.fchmod` and `os.ftruncate`
  on a descriptor opened read-only earlier (their events carry a descriptor, which is allowed),
  and any C extension that does not emit audit events.
- **Anything we did not think of.** The list above is what we found and tested. A new CPython
  release can also add an unaudited primitive.

## What the runtime policy blocks

- **Process creation** (`subprocess`, `os.system`, `os.exec*`, `os.spawn*`, `posix_spawn`,
  `fork`, `pty.spawn`); **network** (`socket` connect, bind, getaddrinfo, sendto, sendmsg, name
  lookups; `urllib` fails through these); `webbrowser.open`; every `ctypes.*` event and the
  import of `cffi`; process signals, tracing and monitoring hooks and rlimit increases (see the
  routes table).
- **Writes**, creates, truncates, removes, renames, `mkdir`, links, `chmod` and `shutil` copies
  or moves outside the step's working directory (`/dev/null` excepted); `os.chdir` out of it
  (including `..`); registering a later audit hook. Paths are resolved by the policy's own
  symlink walk, so symlinks and `..` do not escape.
- **Reads are allowlisted.** Enforced on the audit events `open` (read mode), `os.listdir` and
  `os.scandir`; `glob` reaches the filesystem through those two, so it is covered. A denied
  open raises `PermissionError: runtime policy denied open for reading`, a denied listing
  `runtime policy denied os.listdir` or `... os.scandir`, never with the path. Opens by file
  descriptor and `listdir(None)` are allowed; opening a directory outside the working
  directory is denied (a directory descriptor would let `dir_fd` writes skip the check).

### Reads allowed

All roots are resolved through symlinks at install time and again on every access.

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

Checked on both the joined path and the resolved path, before any allow rule:

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
- Overhead: one statsmodels OLS step through `LocalBackend`, median of 10 runs: 0.825 s without
  the policy and 0.886 s with it (+0.06 s, +7%), measured on the macOS development machine
  after the hardening.
- Hardening evidence (2 Oct 2026, macOS, Python 3.13.9): the four curated cases through
  `borges run --case X --llm scripted --json` give the same universe sets, statuses, estimates
  and p-values (9 decimals), checkpoint counts, flips and verdicts as
  `cases/X/recorded/events.jsonl`: `checkout_ab` 7 universes, 22 checkpoints, flip
  `u_4e00fbb461`; `red_cards` 30 and 58, `u_a64c6b99f5`; `marp_religiosity` 40 and 118, no flip;
  `marp_norms` 15 and 67, `u_c8c83113b4`. The Linux image was not rebuilt or re-run after the
  hardening.

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
  release would be a gap. See "Routes known to be open" for the measured ones.
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
