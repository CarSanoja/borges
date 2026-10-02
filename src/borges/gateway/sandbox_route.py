from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from borges.gateway.errors import GatewayDenied
from borges.gateway.guard import gateway_call
from borges.identity.actions import ToolAction
from borges.sandbox.backend import BranchBackend, Checkpoint, ExecResult
from borges.telemetry.caller import calling_as

if TYPE_CHECKING:
    from borges.gateway.core import Gateway

EXECUTOR = "harness"


class SandboxRoute:
    def __init__(self, gateway: Gateway) -> None:
        self.gw = gateway

    def _authorize(self, target: str) -> None:
        self.gw.authorize(EXECUTOR, ToolAction(tool="sandbox.exec", target=target))

    def _step_files(self, command: Sequence[str], files: Mapping[str, bytes] | None) -> list[str]:
        policy = self.gw.policy.sandbox
        gw = self.gw
        if not command or command[0] not in policy.allowed_commands:
            raise gw.deny(
                "sandbox",
                f"command {command[:1]!r} is not in the allowed commands {policy.allowed_commands}",
                EXECUTOR,
            )
        prefix = f"{policy.step_dir}/"
        if len(command) != 2 or not command[1].startswith(prefix) or not command[1].endswith(".py"):
            raise gw.deny("sandbox", "only a harness step file may be executed", EXECUTOR)
        if not files or command[1] not in files:
            raise gw.deny("sandbox", "the step file being executed was not supplied", EXECUTOR)
        stray = [name for name in files if not (name.startswith(prefix) and name.endswith(".py"))]
        if stray:
            raise gw.deny(
                "sandbox", f"files outside {prefix}*.py may not be written: {stray[:3]}", EXECUTOR
            )
        return list(files)

    def _check_code(self, files: Mapping[str, bytes], names: list[str]) -> None:
        if not self.gw.policy.sandbox.require_code_guard:
            return
        for name in names:
            text = files[name].decode("utf-8", errors="replace")
            if not self.gw.evidence.covers(text):
                raise self.gw.deny(
                    "code_guard",
                    f"{name} carries code that was never recorded as passing the code guard",
                    EXECUTOR,
                    file=name,
                )

    async def root(self, inner: BranchBackend, files: Mapping[str, bytes]) -> Checkpoint:
        data_file = self.gw.policy.sandbox.data_file
        self._authorize("root")
        stray = [name for name in files if name != data_file]
        if stray:
            raise self.gw.deny(
                "sandbox", f"the root checkpoint may only hold {data_file}: {stray[:3]}", EXECUTOR
            )
        with gateway_call():
            return await inner.root(files)

    async def run(
        self,
        inner: BranchBackend,
        parent: Checkpoint,
        command: Sequence[str],
        files: Mapping[str, bytes] | None,
        timeout_s: float,
    ) -> ExecResult:
        gw = self.gw
        self._authorize(command[0] if command else "none")
        names = self._step_files(command, files)
        assert files is not None
        if timeout_s > gw.policy.sandbox.max_timeout_s:
            raise gw.deny(
                "sandbox",
                f"timeout {timeout_s}s is above the ceiling {gw.policy.sandbox.max_timeout_s}s",
                EXECUTOR,
            )
        self._check_code(files, names)
        try:
            gw.budgets.reserve_exec()
        except GatewayDenied as denied:
            gw.record_denial(denied)
            raise
        async with gw.budgets.exec_slot():
            with gateway_call():
                return await inner.run(parent, command, files=files, timeout_s=timeout_s)

    async def read_file(self, inner: BranchBackend, checkpoint: Checkpoint, path: str) -> bytes:
        self._authorize("read_file")
        with gateway_call():
            return await inner.read_file(checkpoint, path)

    def as_executor(self):
        token = self.gw.identity.token_for(EXECUTOR) if self.gw.identity else None
        return calling_as(principal=self.gw.principal_of(EXECUTOR), agent=EXECUTOR, token=token)
