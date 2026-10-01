from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from borges.analysis.models import DecisionRule
from borges.cases.registry import CaseRegistry
from borges.config import Settings
from borges.runs.models import RunRequest

UPLOAD_TITLE = "Uploaded dataset"


@dataclass(frozen=True)
class ResolvedRun:
    case_id: str | None
    title: str
    question: str
    decision_rule: DecisionRule
    dataset_name: str
    data: bytes
    max_universes: int
    fixtures_dir: Path | None


def resolve_run(
    request: RunRequest,
    registry: CaseRegistry,
    settings: Settings,
    data: bytes | None = None,
    dataset_name: str | None = None,
) -> ResolvedRun:
    """Turn a request into concrete inputs. Raises KeyError for unknown cases, ValueError
    for uploads that lack the question or the decision rule."""
    if request.case_id is not None:
        case = registry.get(request.case_id)
        return ResolvedRun(
            case_id=case.id,
            title=case.title,
            question=request.question or case.question,
            decision_rule=request.decision_rule or case.decision_rule,
            dataset_name=dataset_name or case.dataset_name,
            data=data if data is not None else registry.data_bytes(case.id),
            max_universes=request.max_universes or case.max_universes,
            fixtures_dir=registry.fixtures_dir(case.id),
        )
    if data is None:
        raise ValueError("a run needs either a case_id or uploaded data")
    if not request.question or request.decision_rule is None:
        raise ValueError("an uploaded dataset requires a question and a decision rule")
    return ResolvedRun(
        case_id=None,
        title=UPLOAD_TITLE,
        question=request.question,
        decision_rule=request.decision_rule,
        dataset_name=dataset_name or "upload",
        data=data,
        max_universes=request.max_universes or settings.borges_max_universes,
        fixtures_dir=None,
    )
