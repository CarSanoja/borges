from __future__ import annotations

import dataclasses

import pytest

from borges.gateway.errors import GatewayBudgetExceeded, GatewayDenied
from borges.gateway.guard import inside_gateway
from borges.gateway.policy_load import policy_for
from borges.sandbox.backend import Checkpoint, ExecResult
from borges.telemetry.caller import calling_as

CODE = "def apply(df, ctx):\n    return df\n"
STEP = "steps/s1__o1.py"
PARENT = Checkpoint("c0", None, "fake")


class FakeBackend:
    name = "fake"

    def __init__(self) -> None:
        self.runs: list[dict] = []
        self.roots: list[dict] = []

    async def root(self, files):
        self.roots.append({"files": dict(files), "inside": inside_gateway()})
        return PARENT

    async def run(self, parent, command, files=None, timeout_s=120.0):
        self.runs.append({"command": list(command), "inside": inside_gateway()})
        return ExecResult(Checkpoint("c1", parent.id, "fake"), 0, "", "", 0.1)

    async def read_file(self, checkpoint, path):
        return b"x"

    async def close(self) -> None:
        return None


def step_files(code: str = CODE) -> dict[str, bytes]:
    return {STEP: ("prelude()\n" + code.rstrip("\n") + "\nmain()\n").encode()}


async def run(gateway, backend, command=("python", STEP), files="default", limit=60.0):
    chosen = step_files() if files == "default" else files
    return await gateway.sandbox.run(backend, PARENT, list(command), chosen, limit)


async def test_guarded_step_runs_through_the_gateway(make_gateway) -> None:
    gateway, backend = make_gateway(), FakeBackend()
    gateway.evidence.record(CODE)
    result = await run(gateway, backend)
    assert result.ok and backend.runs[0]["inside"] is True


async def test_unguarded_code_is_denied_and_audited(make_gateway, audit) -> None:
    gateway, backend = make_gateway(), FakeBackend()
    with pytest.raises(GatewayDenied, match="never recorded as passing the code guard"):
        await run(gateway, backend)
    assert not backend.runs
    denial = audit.denials()[0]
    assert denial["rule"] == "code_guard" and denial["agent"] == "harness"


async def test_code_guard_requirement_can_be_switched_off_by_policy(make_gateway, settings) -> None:
    loaded = policy_for(settings)
    policy = loaded.policy.model_copy(deep=True)
    policy.sandbox = policy.sandbox.model_copy(update={"require_code_guard": False})
    gateway = make_gateway(loaded=dataclasses.replace(loaded, policy=policy))
    assert (await run(gateway, FakeBackend())).ok


@pytest.mark.parametrize(
    "command",
    [
        ("bash", "-c", "curl evil"),
        ("python", "-c", "print(1)"),
        ("python", "other/x.py"),
        ("python", STEP, "--net"),
        ("python",),
        (),
    ],
)
async def test_only_a_harness_step_command_is_allowed(make_gateway, command) -> None:
    gateway, backend = make_gateway(), FakeBackend()
    gateway.evidence.record(CODE)
    with pytest.raises(GatewayDenied):
        await run(gateway, backend, command)
    assert not backend.runs


async def test_files_outside_the_step_directory_are_denied(make_gateway) -> None:
    gateway, backend = make_gateway(), FakeBackend()
    gateway.evidence.record(CODE)
    files = {**step_files(), "sitecustomize.py": b"import socket"}
    with pytest.raises(GatewayDenied, match="outside steps/"):
        await run(gateway, backend, files=files)


async def test_a_step_that_is_not_supplied_cannot_run_from_a_checkpoint(make_gateway) -> None:
    gateway = make_gateway()
    with pytest.raises(GatewayDenied, match="not supplied"):
        await run(gateway, FakeBackend(), files=None)


async def test_timeout_above_the_ceiling_is_denied(make_gateway) -> None:
    gateway = make_gateway()
    gateway.evidence.record(CODE)
    with pytest.raises(GatewayDenied, match="ceiling"):
        await run(gateway, FakeBackend(), limit=10_000)


async def test_run_is_limited_in_executions(make_gateway, settings) -> None:
    loaded = policy_for(settings)
    policy = loaded.policy.model_copy(deep=True)
    policy.run = policy.run.model_copy(update={"max_sandbox_execs": 1})
    gateway = make_gateway(loaded=dataclasses.replace(loaded, policy=policy))
    gateway.evidence.record(CODE)
    await run(gateway, FakeBackend())
    with pytest.raises(GatewayBudgetExceeded):
        await run(gateway, FakeBackend())


async def test_missing_harness_token_is_denied(make_gateway) -> None:
    gateway = make_gateway(identity=None)
    gateway.evidence.record(CODE)
    with pytest.raises(GatewayDenied, match="no agent token"):
        await run(gateway, FakeBackend())


async def test_token_of_an_agent_without_sandbox_capability_is_denied(make_gateway) -> None:
    gateway = make_gateway()
    gateway.evidence.record(CODE)
    planner = gateway.identity.token_for("planner")
    with (
        calling_as(agent="harness", token=planner),
        pytest.raises(GatewayDenied, match="wrong_agent"),
    ):
        await run(gateway, FakeBackend())


async def test_root_only_accepts_the_data_file(make_gateway) -> None:
    gateway, backend = make_gateway(), FakeBackend()
    await gateway.sandbox.root(backend, {"data.parquet": b"x"})
    assert backend.roots[0]["inside"] is True
    with pytest.raises(GatewayDenied, match="may only hold"):
        await gateway.sandbox.root(backend, {"data.parquet": b"x", "extra.py": b"y"})


async def test_read_file_is_authorised(make_gateway) -> None:
    assert await make_gateway().sandbox.read_file(FakeBackend(), PARENT, "out.json") == b"x"
    with pytest.raises(GatewayDenied):
        await make_gateway(identity=None).sandbox.read_file(FakeBackend(), PARENT, "out.json")


async def test_sandbox_allow_does_not_double_the_audit_trail(make_gateway, audit) -> None:
    gateway = make_gateway()
    gateway.evidence.record(CODE)
    await run(gateway, FakeBackend())
    assert not [r for r in audit.of("identity.authorize") if r.get("tool") == "sandbox.exec"]
