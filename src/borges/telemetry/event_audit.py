from __future__ import annotations

from typing import Any

from borges.fleet.principal import agent_principal
from borges.telemetry import hooks
from borges.telemetry.redaction import redact_text

REASON_CHARS = 300


def _text(value: Any) -> str | None:
    return redact_text(value, REASON_CHARS) if value else None


def audit_agents(agents: Any) -> None:
    if not agents:
        return
    hooks.audit(
        "registry.provenance",
        registry_sha=agents.get("registry_sha"),
        agents=[
            {
                "agent_id": a.get("agent_id"),
                "version": a.get("version"),
                "definition_sha": a.get("definition_sha"),
                "approval": a.get("approval"),
            }
            for a in agents.get("agents", [])
        ],
    )


def audit_run_event(event_type: str, data: dict[str, Any]) -> None:
    match event_type:
        case "run.started":
            hooks.audit(
                "run.lifecycle",
                reason="started",
                case_id=data.get("case_id"),
                llm=data.get("llm"),
                backend=data.get("backend"),
                models=data.get("models"),
                max_universes=data.get("max_universes"),
            )
            audit_agents(data.get("agents"))
        case "run.finished":
            hooks.audit(
                "run.lifecycle",
                reason=str(data.get("status")),
                elapsed_s=data.get("elapsed_s"),
            )
        case "run.failed":
            hooks.audit(
                "run.lifecycle", decision="deny", reason=_text(data.get("error")), status="failed"
            )
        case "option.judged":
            hooks.audit(
                "verdict.judge",
                decision="allow" if data.get("accepted") else "deny",
                reason=_text(data.get("reason")),
                principal=agent_principal("judge"),
                step_id=data.get("step_id"),
                option_id=data.get("option_id"),
                defensibility=data.get("defensibility"),
                origin=data.get("origin"),
            )
        case "option.reviewed":
            faithful = bool(data.get("faithful")) and not data.get("changes_estimand")
            hooks.audit(
                "verdict.reviewer",
                decision="allow" if faithful else "deny",
                reason=_text(data.get("problem")),
                principal=agent_principal("reviewer"),
                step_id=data.get("step_id"),
                option_id=data.get("option_id"),
                faithful=data.get("faithful"),
                changes_estimand=data.get("changes_estimand"),
            )
        case "flip.verified":
            flip = data.get("flip") or {}
            reproduced = flip.get("reproduced")
            hooks.audit(
                "verdict.verifier",
                decision="deny" if reproduced is False else "allow",
                reason="flip did not reproduce" if reproduced is False else None,
                principal="verifier",
                universe_id=flip.get("universe_id"),
                reproduced=reproduced,
                baseline_verdict=flip.get("baseline_verdict"),
                flipped_verdict=flip.get("flipped_verdict"),
            )
