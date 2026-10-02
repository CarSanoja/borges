from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager

from borges.config import Settings
from borges.fleet.principal import agent_principal
from borges.gateway.armor_hooks import Armor, NoopArmor
from borges.gateway.breaker import BreakerRegistry
from borges.gateway.budgets import BudgetBook
from borges.gateway.code_evidence import CodeEvidence, collecting
from borges.gateway.errors import GatewayDenied
from borges.gateway.policy_load import LoadedPolicy, policy_for
from borges.identity.actions import ToolAction
from borges.identity.agent_tokens import AgentTokenInvalid
from borges.identity.authorizer import AgentAuthorizer, AuditSink, CapabilityDenied
from borges.identity.fleet_authorizer import fleet_authorizer, settings_audit_sink
from borges.identity.run_identity import RunIdentity
from borges.telemetry.caller import current_caller

Sleep = Callable[[float], Awaitable[None]]


def quiet_sandbox_allows(sink: AuditSink) -> AuditSink:
    def emit(kind: str, **fields: object) -> None:
        if fields.get("decision") == "allow" and fields.get("tool") == "sandbox.exec":
            return
        sink(kind, **fields)

    return emit


class Gateway:
    """The single choke point for model calls and sandbox executions of one run."""

    def __init__(
        self,
        settings: Settings,
        run_id: str,
        identity: RunIdentity | None,
        loaded: LoadedPolicy,
        authorizer: AgentAuthorizer,
        audit: AuditSink,
        *,
        armor: Armor | None = None,
        local_model: str | None = None,
        dataset_columns: frozenset[str] = frozenset(),
        clock: Callable[[], float] = time.monotonic,
        sleep: Sleep = asyncio.sleep,
        rng: Callable[[], float] = random.random,
    ) -> None:
        from borges.gateway.llm_route import LLMRoute
        from borges.gateway.sandbox_route import SandboxRoute

        self.settings = settings
        self.run_id = run_id
        self.identity = identity
        self.loaded = loaded
        self.policy = loaded.policy
        self.policy_sha = loaded.sha
        self.authorizer = authorizer
        self.audit = audit
        self.armor: Armor = armor or NoopArmor()
        self.local_model = local_model
        self.dataset_columns = dataset_columns
        self.sleep = sleep
        self.rng = rng
        self.budgets = BudgetBook(self.policy)
        self.breakers = BreakerRegistry(self.policy.breaker, clock)
        self.evidence = CodeEvidence()
        self.llm = LLMRoute(self)
        self.sandbox = SandboxRoute(self)

    @contextmanager
    def bind(self) -> Iterator[None]:
        with collecting(self.evidence):
            yield

    def principal_of(self, agent_id: str) -> str:
        grant = self.authorizer.grant(agent_id)
        return grant.principal_id if grant is not None else agent_principal(agent_id)

    def deny(
        self, rule: str, reason: str, agent_id: str | None = None, **data: object
    ) -> GatewayDenied:
        error = GatewayDenied(rule, reason, agent_id)
        self.record_denial(error, **data)
        return error

    def record_denial(self, error: GatewayDenied, **data: object) -> None:
        error.audited = True
        agent_id = error.agent_id
        self.audit(
            "gateway.deny",
            decision="deny",
            reason=error.reason,
            principal=self.principal_of(agent_id) if agent_id else None,
            rule=error.rule,
            agent=agent_id,
            policy_sha=self.policy_sha,
            **data,
        )

    def authorize(self, agent_id: str, action: ToolAction) -> None:
        caller = current_caller()
        token = caller.token if caller.agent == agent_id and caller.token else None
        if token is None and self.identity is not None:
            token = self.identity.token_for(agent_id)
        if token is None:
            raise self.deny(
                "identity",
                f"no agent token for {agent_id!r} in this run",
                agent_id,
                tool=action.tool,
            )
        try:
            self.authorizer.authorize_token(
                token, self.run_id, action, principal=self.principal_of(agent_id)
            )
        except AgentTokenInvalid as invalid:
            raise self.deny("identity", str(invalid), agent_id, tool=action.tool) from invalid
        except CapabilityDenied as denied:
            reason = "; ".join(denied.verdict.reasons)
            raise self.deny("capability", reason, agent_id, tool=action.tool) from denied


def build_gateway(
    settings: Settings,
    run_id: str,
    identity: RunIdentity | None,
    llm_mode: str = "scripted",
    armor: Armor | None = None,
    dataset_columns: frozenset[str] = frozenset(),
) -> Gateway:
    loaded = policy_for(settings)
    sink = settings_audit_sink(settings)
    authorizer = fleet_authorizer(settings, audit=quiet_sandbox_allows(sink))
    local_model = settings.borges_local_model if llm_mode == "local" else None
    return Gateway(
        settings,
        run_id,
        identity,
        loaded,
        authorizer,
        sink,
        armor=armor,
        local_model=local_model,
        dataset_columns=dataset_columns,
    )
