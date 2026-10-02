from __future__ import annotations

from borges.llm.client import BudgetExceeded


class PolicyError(RuntimeError):
    pass


class GatewayDenied(PermissionError):
    def __init__(self, rule: str, reason: str, agent_id: str | None = None) -> None:
        super().__init__(f"gateway denied ({rule}): {reason}")
        self.rule = rule
        self.reason = reason
        self.agent_id = agent_id
        self.audited = False


class GatewayBudgetExceeded(GatewayDenied, BudgetExceeded):
    pass


class GatewayUnavailable(GatewayDenied):
    pass
