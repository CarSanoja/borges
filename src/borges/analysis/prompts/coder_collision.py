from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Option

COLLISION = "collision"
SCALE = "scale"


def collision_instruction(target: Option, other: Option) -> str:
    return (
        f"Smoke check failed for option {target.id}: its code produced exactly the same output "
        f"as option {other.id} on the sample, although the two specs differ.\n"
        f"Spec of {target.id} (this option): {target.spec}\n"
        f"Spec of {other.id}: {other.spec}\n"
        "The two codes produce the same output although the specs differ, so this option's code "
        "must implement exactly its own spec and nothing of the other one. Your previous code:\n"
        f"{target.code}\nWrite new code from this option's spec."
    )


def scale_instruction_for_pair(plan: AnalysisPlan, target: Option, other: Option) -> str:
    return (
        f"Smoke check failed for option {target.id}: it and option {other.id} give the same "
        "p-value and n but estimates on different scales, so they are the same fit reported "
        "differently.\n"
        f"Decision rule metric: {plan.decision_rule.metric}.\n"
        f"Spec of {target.id} (this option): {target.spec}\n"
        f"Spec of {other.id}: {other.spec}\n"
        f"Report estimate, ci_low and ci_high on the scale of the metric "
        f"({plan.decision_rule.metric}), exactly as the spec of this option says. Your previous "
        f"code:\n{target.code}\nWrite new code from this option's spec."
    )


def rewrite_instruction(plan: AnalysisPlan, kind: str, target: Option, other: Option) -> str:
    if kind == SCALE:
        return scale_instruction_for_pair(plan, target, other)
    return collision_instruction(target, other)
