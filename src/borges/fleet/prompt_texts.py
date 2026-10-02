from __future__ import annotations

from borges.analysis.prompts import adversary, coder, judge, narrator, planner, reviewer
from borges.analysis.prompts.coder_recode import recode_instruction


def system_prompt(agent_id: str) -> str | None:
    match agent_id:
        case "planner":
            return planner.SYSTEM
        case "coder":
            return coder.SYSTEM
        case "repairer":
            return f"{coder.SYSTEM}\n\n{recode_instruction([])}"
        case "adversary":
            return adversary.SYSTEM
        case "judge":
            return judge.SYSTEM
        case "reviewer":
            return reviewer.SYSTEM
        case "narrator":
            return narrator.SYSTEM
    return None
