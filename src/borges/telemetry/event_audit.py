from __future__ import annotations

from typing import Any

from borges.telemetry import hooks

REASON_CHARS = 300


def _text(value: Any) -> str | None:
    return str(value)[:REASON_CHARS] if value else None


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
                principal="agent:judge",
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
                principal="agent:reviewer",
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
