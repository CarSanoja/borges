from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any

from borges.gateway.errors import GatewayDenied
from borges.sandbox.backend import BranchBackend, Checkpoint, ExecResult
from borges.telemetry import hooks
from borges.telemetry.caller import current_caller
from borges.telemetry.hashing import sha256_json

if TYPE_CHECKING:
    from borges.gateway.core import Gateway


class InstrumentedBackend:
    """Wraps a BranchBackend so every sandbox call goes through the gateway, a span and an audit."""

    def __init__(self, inner: BranchBackend, gateway: Gateway | None = None) -> None:
        self._inner = inner
        self._gateway = gateway

    def _scope(self):
        return self._gateway.sandbox.as_executor() if self._gateway else nullcontext()

    def _policy(self) -> dict[str, Any]:
        if self._gateway is None:
            return {}
        return {"decision": "allow", "policy_sha": self._gateway.policy_sha}

    async def _root(self, files: Mapping[str, bytes]) -> Checkpoint:
        if self._gateway is None:
            return await self._inner.root(files)
        return await self._gateway.sandbox.root(self._inner, files)

    async def _run(
        self,
        parent: Checkpoint,
        command: Sequence[str],
        files: Mapping[str, bytes] | None,
        timeout_s: float,
    ) -> ExecResult:
        if self._gateway is None:
            return await self._inner.run(parent, command, files=files, timeout_s=timeout_s)
        return await self._gateway.sandbox.run(self._inner, parent, command, files, timeout_s)

    @property
    def name(self) -> str:
        return self._inner.name

    def __getattr__(self, name: str) -> Any:
        value = getattr(self._inner, name)
        if callable(value):
            raise AttributeError(f"{name} is not reachable except through the gateway")
        return value

    async def root(self, files: Mapping[str, bytes]) -> Checkpoint:
        with self._scope():
            return await self._traced_root(files)

    async def _traced_root(self, files: Mapping[str, bytes]) -> Checkpoint:
        if hooks.current() is None:
            return await self._root(files)
        attributes = {"borges.sandbox.backend": self.name, "borges.sandbox.files": len(files)}
        with hooks.span("sandbox_root", "sandbox.root", **attributes) as span:
            checkpoint = await self._root(files)
            span.set_attribute("borges.checkpoint.id", checkpoint.id)
            hooks.audit(
                "sandbox.root",
                principal=current_caller().principal,
                backend=self.name,
                checkpoint=checkpoint.id,
                files=len(files),
                **self._policy(),
            )
            return checkpoint

    async def run(
        self,
        parent: Checkpoint,
        command: Sequence[str],
        files: Mapping[str, bytes] | None = None,
        timeout_s: float = 120.0,
    ) -> ExecResult:
        with self._scope():
            return await self._traced_run(parent, command, files, timeout_s)

    async def _traced_run(
        self,
        parent: Checkpoint,
        command: Sequence[str],
        files: Mapping[str, bytes] | None,
        timeout_s: float,
    ) -> ExecResult:
        if hooks.current() is None:
            return await self._run(parent, command, files, timeout_s)
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
                result = await self._run(parent, command, files, timeout_s)
            except BaseException as exc:
                span.set_attribute("error.type", type(exc).__name__)
                hooks.audit(
                    "sandbox.exec",
                    decision="deny" if isinstance(exc, GatewayDenied) else None,
                    reason=exc.reason if isinstance(exc, GatewayDenied) else None,
                    principal=caller.principal,
                    backend=self.name,
                    step_id=caller.step_id,
                    option_id=caller.option_id,
                    universe_id=caller.universe_id,
                    parent_checkpoint=parent.id,
                    command_sha256=command_hash,
                    outcome="denied" if isinstance(exc, GatewayDenied) else "error",
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
                **self._policy(),
            )
            return result

    async def read_file(self, checkpoint: Checkpoint, path: str) -> bytes:
        if self._gateway is None:
            return await self._inner.read_file(checkpoint, path)
        with self._scope():
            return await self._gateway.sandbox.read_file(self._inner, checkpoint, path)

    async def close(self) -> None:
        await self._inner.close()


def instrument_backend(backend: BranchBackend, gateway: Gateway | None = None) -> BranchBackend:
    if isinstance(backend, InstrumentedBackend):
        return backend
    return InstrumentedBackend(backend, gateway)
