from __future__ import annotations

from collections.abc import Callable

from borges.identity.actions import (
    ActionRisk,
    PermissionDecision,
    PermissionVerdict,
    ToolAction,
)

Rule = Callable[[ToolAction], PermissionDecision | None]


class PermissionRuleError(ValueError):
    pass


def _reason(decision: PermissionDecision, action: ToolAction, rule: Rule) -> str:
    explain = getattr(rule, "permission_reason", None)
    if explain is not None:
        text = explain(action)
        if text:
            return text
    if decision == PermissionDecision.DENY:
        return f"target {action.target!r} is outside the allowed scope for {action.tool}"
    return (
        f"external mutation {action.tool} for {action.target!r} did not clear the confidence gate"
    )


class PermissionGate:
    """First matching DENY wins, then QUARANTINE, otherwise ALLOW."""

    def __init__(self, rules: list[Rule]) -> None:
        if not rules:
            raise PermissionRuleError("permission gate requires at least one rule")
        self._rules = list(rules)

    def evaluate(self, action: ToolAction) -> PermissionVerdict:
        for decision in (PermissionDecision.DENY, PermissionDecision.QUARANTINE):
            for rule in self._rules:
                if rule(action) == decision:
                    return PermissionVerdict(
                        decision=decision,
                        tool=action.tool,
                        target=action.target,
                        reasons=[_reason(decision, action, rule)],
                    )
        return PermissionVerdict(
            decision=PermissionDecision.ALLOW, tool=action.tool, target=action.target
        )


def scope_rule(tool: str, allowed_targets: set[str]) -> Rule:
    def rule(action: ToolAction) -> PermissionDecision | None:
        if action.tool != tool or action.target in allowed_targets:
            return None
        return PermissionDecision.DENY

    return rule


def confidence_rule(tool: str, confidence_key: str, threshold: float) -> Rule:
    def rule(action: ToolAction) -> PermissionDecision | None:
        if action.tool != tool or action.risk != ActionRisk.EXTERNAL_MUTATION:
            return None
        confidence = action.payload.get(confidence_key)
        if isinstance(confidence, int | float) and float(confidence) >= threshold:
            return None
        return PermissionDecision.QUARANTINE

    return rule
