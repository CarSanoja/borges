from __future__ import annotations

from typing import Any

import pytest

from borges.config import Settings
from borges.identity.actions import ActionRisk, PermissionDecision, ToolAction
from borges.identity.agent_tokens import AgentTokenInvalid, AgentTokenIssuer
from borges.identity.authorizer import (
    AgentAuthorizer,
    AgentGrant,
    CapabilityDenied,
    tool_capability_resolver,
)
from borges.identity.capability_ledger import capability_scope
from borges.identity.fleet_authorizer import fleet_authorizer
from borges.identity.permission_gate import PermissionGate, confidence_rule
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import global_audit_path

PLANNER = "agent://borges/planner"


class Sink:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, kind: str, **fields: Any) -> None:
        self.calls.append((kind, fields))


def build(sink: Sink, issuer: AgentTokenIssuer | None = None) -> AgentAuthorizer:
    resolver = tool_capability_resolver(
        {"sandbox.exec": "sandbox.exec"}, {"model.invoke": lambda a: f"llm.invoke:{a.target}"}
    )
    grants = [AgentGrant("planner", PLANNER, frozenset({"llm.invoke:m1", "spend.use"}))]
    return AgentAuthorizer(grants, resolver, issuer, sink)


def model(target: str = "m1") -> ToolAction:
    return ToolAction(tool="model.invoke", target=target, risk=ActionRisk.PASSIVE)


def test_held_capability_is_allowed_and_audited() -> None:
    sink = Sink()
    verdict = build(sink).authorize("planner", model())
    assert verdict.allowed
    kind, fields = sink.calls[0]
    assert kind == "identity.authorize"
    assert fields["decision"] == "allow" and fields["principal"] == PLANNER


def test_missing_capability_is_denied_and_audited() -> None:
    sink = Sink()
    with pytest.raises(CapabilityDenied, match="llm.invoke:m2"):
        build(sink).authorize("planner", model("m2"))
    assert sink.calls[0][1]["decision"] == "deny"


def test_unknown_agent_fails_closed() -> None:
    sink = Sink()
    with pytest.raises(CapabilityDenied, match="not declared"):
        build(sink).authorize("ghost", model())
    assert sink.calls[0][1]["principal"] == "unknown"


def test_unmapped_action_fails_closed() -> None:
    with pytest.raises(CapabilityDenied, match="maps to no declared capability"):
        build(Sink()).authorize(
            "planner", ToolAction(tool="shell.rm", target="/", risk=ActionRisk.INTERNAL_MUTATION)
        )


def test_gate_quarantine_is_a_denial_in_the_audit_log() -> None:
    sink = Sink()
    authorizer = build(sink)
    gate = PermissionGate([confidence_rule("sandbox.exec", "c", 0.9)])
    authorizer = AgentAuthorizer(
        [AgentGrant("planner", PLANNER, frozenset({"sandbox.exec"}))],
        tool_capability_resolver({"sandbox.exec": "sandbox.exec"}),
        audit=sink,
    )
    action = ToolAction(tool="sandbox.exec", target="x", risk=ActionRisk.EXTERNAL_MUTATION)
    with pytest.raises(CapabilityDenied) as caught:
        authorizer.authorize("planner", action, gate=gate)
    assert caught.value.verdict.decision == PermissionDecision.QUARANTINE
    assert sink.calls[0][1]["decision"] == "deny"
    assert sink.calls[0][1]["verdict"] == "quarantine"


def test_ledger_collects_decisions_in_scope() -> None:
    authorizer = build(Sink())
    with capability_scope() as ledger:
        authorizer.authorize("planner", model())
        with pytest.raises(CapabilityDenied):
            authorizer.authorize("planner", model("m2"))
    assert len(ledger.records) == 2 and len(ledger.denials) == 1


def test_token_authorization_intersects_claims_with_the_grant() -> None:
    issuer = AgentTokenIssuer(secret=b"k" * 32)
    authorizer = build(Sink(), issuer)
    wide = issuer.mint("r1", PLANNER, ["llm.invoke:m1", "sandbox.exec"], 60)
    assert authorizer.authorize_token(wide, "r1", model()).allowed
    narrow = issuer.mint("r1", PLANNER, ["spend.use"], 60)
    with pytest.raises(CapabilityDenied):
        authorizer.authorize_token(narrow, "r1", model())


def test_forged_expired_and_wrong_run_tokens_are_rejected_and_audited() -> None:
    now = [1000.0]
    issuer = AgentTokenIssuer(secret=b"k" * 32, clock=lambda: now[0])
    sink = Sink()
    authorizer = build(sink, issuer)
    good = issuer.mint("r1", PLANNER, ["llm.invoke:m1"], 60)
    forged = AgentTokenIssuer(secret=b"z" * 32).mint("r1", PLANNER, ["llm.invoke:m1"], 60)
    with pytest.raises(AgentTokenInvalid) as forged_error:
        authorizer.authorize_token(forged, "r1", model())
    with pytest.raises(AgentTokenInvalid) as run_error:
        authorizer.authorize_token(good, "r2", model())
    now[0] += 61
    with pytest.raises(AgentTokenInvalid) as expired_error:
        authorizer.authorize_token(good, "r1", model())
    assert [forged_error.value.failure, run_error.value.failure, expired_error.value.failure] == [
        "bad_signature",
        "wrong_run",
        "expired",
    ]
    assert all(fields["decision"] == "deny" for _, fields in sink.calls)
    assert len(sink.calls) == 3


def test_token_for_an_agent_missing_from_the_fleet_is_denied() -> None:
    issuer = AgentTokenIssuer(secret=b"k" * 32)
    token = issuer.mint("r1", "agent://borges/ghost", ["spend.use"], 60)
    with pytest.raises(CapabilityDenied, match="not declared"):
        build(Sink(), issuer).authorize_token(token, "r1", model())


def test_fleet_authorizer_reads_capabilities_from_the_fleet(tmp_path) -> None:
    settings = Settings(_env_file=None, borges_home=tmp_path / "h")
    authorizer = fleet_authorizer(settings)
    assert "planner" in authorizer.agent_ids and "harness" in authorizer.agent_ids
    exec_action = ToolAction(tool="sandbox.exec", target="x", risk=ActionRisk.INTERNAL_MUTATION)
    assert authorizer.authorize("harness", exec_action).allowed
    with pytest.raises(CapabilityDenied):
        authorizer.authorize("planner", exec_action)
    decisions = [r.decision for r in read_records(global_audit_path(settings))]
    assert decisions == ["allow", "deny"]
