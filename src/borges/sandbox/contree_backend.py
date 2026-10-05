from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import PurePosixPath
from typing import Any

from borges.sandbox.backend import WORKDIR, Checkpoint, ExecResult, SandboxError

INSTALL_COMMAND = "pip install --no-cache-dir pandas numpy scipy statsmodels pyarrow"
IMPORT_CHECK_COMMAND = "python -c 'import pandas, numpy, scipy, statsmodels, pyarrow'"
INSTALL_TIMEOUT_S = 900.0
CHECK_TIMEOUT_S = 120.0
STDERR_TAIL_CHARS = 400
TRANSIENT_WAITS_S = (1.0, 4.0)
EXPIRED_FILES = "Files not found or expired"


def _remote_files(files: Mapping[str, bytes] | None) -> dict[str, bytes]:
    return {str(PurePosixPath(WORKDIR) / rel): data for rel, data in (files or {}).items()}


def _remote_path(path: str) -> str:
    target = PurePosixPath(WORKDIR) / path
    parts: list[str] = []
    for part in target.parts[1:]:
        if part == "..":
            if not parts:
                raise SandboxError(f"path escapes the sandbox: {path!r}")
            parts.pop()
        elif part != ".":
            parts.append(part)
    resolved = PurePosixPath("/", *parts)
    root = PurePosixPath(WORKDIR)
    if resolved != root and root not in resolved.parents:
        raise SandboxError(f"path escapes the sandbox: {path!r}")
    return str(resolved)


class ContreeBackend:
    """Nebius Token Factory sandboxes: every run is a non-disposable image run on the parent."""

    name = "contree"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        base_image: str = "docker://python:3.13-slim",
        runner_tag: str = "borges-runner-1",
        project_id: str | None = None,
    ) -> None:
        try:
            from contree_sdk import Contree
            from contree_sdk.auth import IAMAuth
            from contree_sdk.config import ContreeConfig
        except ImportError as exc:
            raise SandboxError(
                "the contree backend needs the optional dependency: install borges[contree]"
            ) from exc
        auth = IAMAuth(base_url=base_url, token=api_key)
        if project_id:
            auth = replace(auth, project_id=project_id)
        self._client = Contree(ContreeConfig(auth=auth))
        self.base_image = base_image
        self.runner_tag = runner_tag
        self._runner: Any | None = None
        self._runner_lock = asyncio.Lock()
        self._images: dict[str, Any] = {}

    async def ensure_runner_image(self) -> Any:
        async with self._runner_lock:
            if self._runner is not None:
                return self._runner
            from contree_sdk.sdk.exceptions import ContreeError, NotFoundError

            images = self._client.images
            try:
                self._runner = await images.use(self.runner_tag, strict=True)
            except NotFoundError:
                try:
                    base = await images.oci(self.base_image)
                    installed = await base.run(
                        shell=INSTALL_COMMAND, timeout=INSTALL_TIMEOUT_S, disposable=False
                    )
                    _require_success(installed, "install the analysis packages")
                    checked = await installed.run(
                        shell=IMPORT_CHECK_COMMAND, timeout=CHECK_TIMEOUT_S, disposable=True
                    )
                    _require_success(checked, "import the analysis packages")
                    self._runner = await installed.tag_as(self.runner_tag)
                except ContreeError as exc:
                    raise SandboxError(f"could not build the runner image: {exc}") from exc
            return self._runner

    async def root(self, files: Mapping[str, bytes]) -> Checkpoint:
        from contree_sdk.sdk.exceptions import ContreeError

        runner = await self.ensure_runner_image()
        try:
            image = await runner.run(
                shell=f"mkdir -p {WORKDIR}", files=_remote_files(files), disposable=False
            )
        except ContreeError as exc:
            raise SandboxError(f"could not create the root checkpoint: {exc}") from exc
        return self._remember(image, None)

    def _remember(self, image: Any, parent_id: str | None) -> Checkpoint:
        if image.uuid is None:
            raise SandboxError("contree returned no image for a non-disposable run")
        checkpoint = Checkpoint(str(image.uuid), parent_id, self.name)
        self._images[checkpoint.id] = image
        return checkpoint

    async def _image_for(self, checkpoint: Checkpoint) -> Any:
        image = self._images.get(checkpoint.id)
        if image is None:
            image = await self._client.images.use(checkpoint.id)
            self._images[checkpoint.id] = image
        return image

    async def run(
        self,
        parent: Checkpoint,
        command: Sequence[str],
        files: Mapping[str, bytes] | None = None,
        timeout_s: float = 120.0,
    ) -> ExecResult:
        from contree_sdk.sdk.exceptions import ContreeError

        if not command:
            raise SandboxError("empty command")
        base = await self._image_for(parent)
        started = time.perf_counter()
        arguments = {"command": command[0], "args": list(command[1:]), "cwd": WORKDIR}
        try:
            image = await _run_with_retries(
                base, files=_remote_files(files), timeout=timeout_s, disposable=False, **arguments
            )
        except ContreeError as exc:
            raise SandboxError(f"contree run failed: {exc}") from exc
        duration = time.perf_counter() - started
        checkpoint = self._remember(image, parent.id)
        result = image.result
        return ExecResult(
            checkpoint=checkpoint,
            exit_code=int(result.exit_code),
            stdout=_as_text(result.stdout),
            stderr=_as_text(result.stderr),
            duration_s=duration,
        )

    async def read_file(self, checkpoint: Checkpoint, path: str) -> bytes:
        from contree_sdk.sdk.exceptions import ContreeError

        remote = _remote_path(path)
        image = await self._image_for(checkpoint)
        try:
            return await image.read(remote)
        except ContreeError as exc:
            raise SandboxError(f"no such file in {checkpoint.id}: {path} ({exc})") from exc

    async def close(self) -> None:
        return None


async def _run_with_retries(base: Any, **arguments: Any) -> Any:
    """A run is a pure function of its parent image, so a transport failure is safe to retry.

    So is an upload the service let expire between the client's lookup by hash and the run: at
    d29a189 seven marp_norms universes failed within one second with "Files not found or
    expired", and the same universes ran when the search came back to them."""
    from contree_sdk.sdk.exceptions import ApiTimeoutError, ContreeTransportError, NotFoundError

    for wait in TRANSIENT_WAITS_S:
        try:
            return await base.run(**arguments)
        except (ApiTimeoutError, ContreeTransportError):
            await asyncio.sleep(wait)
        except NotFoundError as exc:
            if EXPIRED_FILES not in str(exc):
                raise
            await asyncio.sleep(wait)
    return await base.run(**arguments)


def _require_success(image: Any, action: str) -> None:
    result = image.result
    if int(result.exit_code) != 0:
        tail = _as_text(result.stderr).strip()[-STDERR_TAIL_CHARS:]
        raise SandboxError(f"could not build the runner image: failed to {action}: {tail}")


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value)
