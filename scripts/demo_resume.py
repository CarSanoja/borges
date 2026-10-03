from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WORKER = ["-c", "from borges.cli import app; app()", "runs", "work"]
POLL_S = 0.02


def scratch_env(root: Path) -> dict[str, str]:
    env = {**os.environ}
    env.update(BORGES_HOME=str(root / "home"), BORGES_RUNS_DIR=str(root / "runs"))
    for name in ("BORGES_STORE_KEY", "BORGES_AUDIT_ANCHOR_KEY", "BORGES_MEMORY_KEY"):
        env.pop(name, None)
    env["BORGES_MEMORY"] = "false"
    return env


def start_worker(env: dict[str, str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, *WORKER],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def submit(case: str) -> str:
    from borges.cases.registry import CaseRegistry
    from borges.config import get_settings
    from borges.identity.principal import ANONYMOUS
    from borges.runs.bus import EventBus
    from borges.runs.models import RunRequest
    from borges.runs.orchestrator import RunOrchestrator
    from borges.runs.store import RunStore
    from borges.runtime.runtime import Runtime
    from borges.runtime.submission import submit_run

    settings = get_settings()
    store = RunStore(settings.borges_runs_dir)
    bus = EventBus(store)
    orchestrator = RunOrchestrator(settings, store, bus, CaseRegistry(settings.borges_cases_dir))
    runtime = Runtime(settings, orchestrator, store, bus)
    request = RunRequest(case_id=case, llm="scripted")
    result = await submit_run(runtime, request, ANONYMOUS, "demo", None, None, None, "demo", None)
    return result.run_id


def universes_done(run_id: str) -> int:
    from borges.config import get_settings
    from borges.runtime.checkpoints import SqliteCheckpointStore
    from borges.runtime.db import open_runtime_db
    from borges.runtime.universe_checkpoint import UNIVERSE_PREFIX

    store = SqliteCheckpointStore(open_runtime_db(get_settings()))
    return len(store.with_prefix(run_id, UNIVERSE_PREFIX))


def snapshot(run_id: str):
    from borges.config import get_settings
    from borges.runs.store import RunStore

    return RunStore(get_settings().borges_runs_dir).snapshot(run_id)


def wait_for_progress(worker: subprocess.Popen[bytes], run_id: str, wanted: int) -> int:
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        if worker.poll() is not None:
            return -1
        done = universes_done(run_id)
        if done >= wanted:
            return done
        time.sleep(POLL_S)
    return -1


def run_to_completion(root: Path, case: str) -> str:
    os.environ.update(scratch_env(root))
    run_id = asyncio.run(submit(case))
    worker = start_worker(scratch_env(root))
    worker.wait(timeout=900)
    return run_id


def describe(label: str, run_id: str) -> tuple[str | None, str | None]:
    snap = snapshot(run_id)
    flip = snap.flip
    flipped = f"{flip.baseline_verdict} -> {flip.flipped_verdict}" if flip else "no flip"
    print(
        f"{label}: {run_id} status={snap.status} universes={len(snap.garden.universes)} "
        f"resumed={snap.resumed} flip={flip.universe_id if flip else None} ({flipped})"
    )
    return (flip.universe_id if flip else None), snap.status


def main() -> int:
    parser = argparse.ArgumentParser(description="Kill a worker mid-garden and resume the run.")
    parser.add_argument("--case", default="checkout_ab")
    parser.add_argument("--kill-after", type=int, default=3)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="borges-demo-resume-") as tmp:
        root = Path(tmp)
        print(f"scratch home {root} (removed at the end)")
        baseline_id = run_to_completion(root / "baseline", args.case)
        expected, status = describe("uninterrupted", baseline_id)
        if status != "completed":
            return 1
        crash = root / "crash"
        os.environ.update(scratch_env(crash))
        run_id = asyncio.run(submit(args.case))
        worker = start_worker(scratch_env(crash))
        done = wait_for_progress(worker, run_id, args.kill_after)
        if done < 0:
            worker.kill()
            print("the worker finished before it could be killed; run the demo again")
            return 2
        worker.kill()
        worker.wait()
        print(f"worker killed (SIGKILL) with {done} universes checkpointed; restarting")
        resumed = start_worker(scratch_env(crash))
        resumed.wait(timeout=900)
        found, status = describe("resumed", run_id)
        same = status == "completed" and found == expected and snapshot(run_id).resumed >= 1
        print("SAME FLIP after the kill and resume" if same else "THE RESUMED RUN DIFFERS")
        return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
