from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from borges.sandbox.backend import BranchBackend, Checkpoint, ExecResult
from borges.telemetry import hooks
from borges.telemetry.caller import current_caller
from borges.telemetry.hashing import sha256_json


class InstrumentedBackend:
    """Wraps a BranchBackend so every sandbox call yields a span and an audit record."""

    def __init__(self, inner: BranchBackend) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    async def root(self, files: Mapping[str, bytes]) -> Checkpoint:
        if hooks.current() is None:
            return await self._inner.root(files)
        attributes = {"borges.sandbox.backend": self.name, "borges.sandbox.files": len(files)}
        with hooks.span("sandbox_root", "sandbox.root", **attributes) as span:
            checkpoint = await self._inner.root(files)
            span.set_attribute("borges.checkpoint.id", checkpoint.id)
            hooks.audit(
                "sandbox.root",
                principal=current_caller().principal,
                backend=self.name,
                checkpoint=checkpoint.id,
                files=len(files),
            )
            return checkpoint

    async def run(
        self,
        parent: Checkpoint,
        command: Sequence[str],
        files: Mapping[str, bytes] | None = None,
        timeout_s: float = 120.0,
    ) -> ExecResult:
        if hooks.current() is None:
            return await self._inner.run(parent, command, files=files, timeout_s=timeout_s)
        caller = current_caller()
        command_hash = sha256_json(list(command))
        attributes = {
            "borges.sandbox.backend": self.name,
            "borges.checkpoint.parent": parent.id,
            "borges.sandbox.command.sha256": command_hash,
            "borges.sandbox.timeout_s": timeout_s,
        }
        if caller.step_id:
            attributes["borges.step_id"] = caller.step_id
        if caller.option_id:
            attributes["borges.option_id"] = caller.option_id
        with hooks.span("sandbox_exec", "sandbox.exec", **attributes) as span:
            try:
                result = await self._inner.run(parent, command, files=files, timeout_s=timeout_s)
            except BaseException as exc:
                span.set_attribute("error.type", type(exc).__name__)
                hooks.audit(
                    "sandbox.exec",
                    principal=caller.principal,
                    backend=self.name,
                    step_id=caller.step_id,
                    option_id=caller.option_id,
                    universe_id=caller.universe_id,
                    parent_checkpoint=parent.id,
                    command_sha256=command_hash,
                    outcome="error",
                    error_type=type(exc).__name__,
                )
                raise
            span.set_attribute("borges.checkpoint.child", result.checkpoint.id)
            span.set_attribute("borges.sandbox.exit_code", result.exit_code)
            span.set_attribute("borges.sandbox.duration_s", result.duration_s)
            hooks.audit(
                "sandbox.exec",
                principal=caller.principal,
                backend=self.name,
                step_id=caller.step_id,
                option_id=caller.option_id,
                universe_id=caller.universe_id,
                parent_checkpoint=parent.id,
                child_checkpoint=result.checkpoint.id,
                command_sha256=command_hash,
                exit_code=result.exit_code,
                duration_s=round(result.duration_s, 4),
                outcome="ok" if result.ok else "failed",
            )
            return result

    async def read_file(self, checkpoint: Checkpoint, path: str) -> bytes:
        return await self._inner.read_file(checkpoint, path)

    async def close(self) -> None:
        await self._inner.close()


def instrument_backend(backend: BranchBackend) -> BranchBackend:
    return backend if isinstance(backend, InstrumentedBackend) else InstrumentedBackend(backend)
