from __future__ import annotations

from typing import Any

from borges.analysis.models import AnalysisPlan, CodingSummary
from borges.runs.judged_ledger import JudgedLedger

PLAN_KEY = "stage:plan"
CODED_KEY = "stage:coded"


def judged_payload(judged: JudgedLedger) -> dict[str, list[dict[str, Any]]]:
    return {
        step_id: [
            {
                "option": entry.option.model_dump(mode="json"),
                "judgement": entry.judgement.model_dump(mode="json"),
            }
            for entry in entries
        ]
        for step_id, entries in judged.entries.items()
    }


def plan_payload(plan: AnalysisPlan, judged: JudgedLedger, coding: CodingSummary) -> dict[str, Any]:
    return {
        "plan": plan.model_dump(mode="json"),
        "judged": judged_payload(judged),
        "coding": coding.model_dump(mode="json"),
    }


def coded_payload(
    plan: AnalysisPlan, judged: JudgedLedger, coding: CodingSummary, smoke_notes: list[str]
) -> dict[str, Any]:
    return {**plan_payload(plan, judged, coding), "smoke_notes": list(smoke_notes)}
