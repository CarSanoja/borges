from __future__ import annotations

import pytest

from borges.identity.actions import ActionRisk, PermissionDecision, ToolAction
from borges.identity.permission_gate import (
    PermissionGate,
    PermissionRuleError,
    confidence_rule,
    scope_rule,
)


def action(tool: str = "report.write", target: str = "a", **payload) -> ToolAction:
    return ToolAction(tool=tool, target=target, risk=ActionRisk.EXTERNAL_MUTATION, payload=payload)


def test_gate_needs_rules() -> None:
    with pytest.raises(PermissionRuleError):
        PermissionGate([])


def test_allow_when_no_rule_objects() -> None:
    gate = PermissionGate([scope_rule("report.write", {"a"})])
    assert gate.evaluate(action()).decision == PermissionDecision.ALLOW


def test_out_of_scope_target_is_denied() -> None:
    gate = PermissionGate([scope_rule("report.write", {"a"})])
    verdict = gate.evaluate(action(target="b"))
    assert verdict.decision == PermissionDecision.DENY
    assert "outside the allowed scope" in verdict.reasons[0]


def test_low_confidence_mutation_is_quarantined() -> None:
    gate = PermissionGate([confidence_rule("report.write", "conf", 0.8)])
    assert gate.evaluate(action(conf=0.5)).decision == PermissionDecision.QUARANTINE
    assert gate.evaluate(action(conf=0.9)).decision == PermissionDecision.ALLOW
    assert gate.evaluate(action()).decision == PermissionDecision.QUARANTINE


def test_deny_beats_quarantine_beats_allow() -> None:
    gate = PermissionGate(
        [confidence_rule("report.write", "conf", 0.8), scope_rule("report.write", {"a"})]
    )
    assert gate.evaluate(action(target="b", conf=0.1)).decision == PermissionDecision.DENY
    assert gate.evaluate(action(target="a", conf=0.1)).decision == PermissionDecision.QUARANTINE
