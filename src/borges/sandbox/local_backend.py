from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path

from borges.sandbox.backend import Checkpoint, ExecResult, SandboxError

TIMEOUT_EXIT_CODE = 124


def _clone_tree(src: Path, dst: Path) -> None:
    if sys.platform == "darwin":
        cmd = ["cp", "-c", "-R", str(src), str(dst)]
    elif sys.platform.startswith("linux"):
        cmd = ["cp", "--reflink=auto", "-a", str(src), str(dst)]
    else:
        shutil.copytree(src, dst, symlinks=True)
        return
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0:
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst, symlinks=True)


def _write_files(fs: Path, files: Mapping[str, bytes]) -> None:
    for rel, data in files.items():
        target = _resolve_inside(fs, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def _resolve_inside(fs: Path, rel: str) -> Path:
    root = fs.resolve()
    target = (root / rel).resolve()
    if target != root and root not in target.parents:
        raise SandboxError(f"path escapes the sandbox: {rel!r}")
    return target


class LocalBackend:
    """Checkpoints as directories; forks are copy-on-write clones where the filesystem allows."""

    name = "local"

    def __init__(self, home: Path, python: str = sys.executable, ephemeral: bool = False) -> None:
        self.home = Path(home)
        self.python = python
        self.ephemeral = ephemeral
        self._base = self.home / "checkpoints"

    def _fs(self, checkpoint_id: str) -> Path:
        return self._base / checkpoint_id / "fs"

    def _new_id(self) -> str:
        return "ck_" + uuid.uuid4().hex[:12]

    def _create(self, parent: Checkpoint | None, files: Mapping[str, bytes]) -> Checkpoint:
        new_id = self._new_id()
        directory = self._base / new_id
        directory.mkdir(parents=True)
        fs = directory / "fs"
        if parent is None:
            fs.mkdir()
        else:
            source = self._fs(parent.id)
            if not source.is_dir():
                shutil.rmtree(directory, ignore_errors=True)
                raise SandboxError(f"unknown checkpoint: {parent.id}")
            _clone_tree(source, fs)
        _write_files(fs, files)
        meta = {"id": new_id, "parent_id": parent.id if parent else None}
        (directory / "meta.json").write_text(json.dumps(meta))
        return Checkpoint(new_id, meta["parent_id"], self.name)

    async def root(self, files: Mapping[str, bytes]) -> Checkpoint:
        return await asyncio.to_thread(self._create, None, dict(files))

    def _env(self, fs: Path) -> dict[str, str]:
        return {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(fs),
            "PYTHONHASHSEED": "0",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "MPLBACKEND": "Agg",
            "LANG": "C.UTF-8",
        }

    async def run(
        self,
        parent: Checkpoint,
        command: Sequence[str],
        files: Mapping[str, bytes] | None = None,
        timeout_s: float = 120.0,
    ) -> ExecResult:
        if not command:
            raise SandboxError("empty command")
        child = await asyncio.to_thread(self._create, parent, dict(files or {}))
        fs = self._fs(child.id)
        argv = [self.python if command[0] == "python" else command[0], *command[1:]]
        started = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                cwd=fs,
                env=self._env(fs),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as exc:
            return ExecResult(child, 127, "", str(exc), time.perf_counter() - started)
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        except TimeoutError:
            self._kill_group(proc)
            out, err = await proc.communicate()
            stderr = err.decode(errors="replace") + f"\ntimeout after {timeout_s}s"
            duration = time.perf_counter() - started
            return ExecResult(
                child, TIMEOUT_EXIT_CODE, out.decode(errors="replace"), stderr, duration
            )
        except asyncio.CancelledError:
            self._kill_group(proc)
            raise
        return ExecResult(
            child,
            proc.returncode if proc.returncode is not None else -1,
            out.decode(errors="replace"),
            err.decode(errors="replace"),
            time.perf_counter() - started,
        )

    @staticmethod
    def _kill_group(proc: asyncio.subprocess.Process) -> None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)

    async def read_file(self, checkpoint: Checkpoint, path: str) -> bytes:
        fs = self._fs(checkpoint.id)
        if not fs.is_dir():
            raise SandboxError(f"unknown checkpoint: {checkpoint.id}")
        target = _resolve_inside(fs, path)
        if not target.is_file():
            raise SandboxError(f"no such file in {checkpoint.id}: {path}")
        return await asyncio.to_thread(target.read_bytes)

    async def close(self) -> None:
        if self.ephemeral:
            await asyncio.to_thread(shutil.rmtree, self.home, True)

    def cleanup(self) -> None:
        shutil.rmtree(self._base, ignore_errors=True)
