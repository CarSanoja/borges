from __future__ import annotations

from borges.cases.registry import CaseRegistry
from borges.fleet.catalog import AnalysisTemplate


def analysis_templates(registry: CaseRegistry) -> list[AnalysisTemplate]:
    templates: list[AnalysisTemplate] = []
    for card in registry.list():
        spec = registry.get(card.id)
        templates.append(
            AnalysisTemplate(
                id=spec.id,
                title=spec.title,
                owner=spec.owner,
                question=spec.question,
                metric=spec.decision_rule.metric,
                decision_rule=spec.decision_rule.model_dump(mode="json"),
                dataset_name=spec.dataset_name,
                live_only=spec.live_only,
            )
        )
    return templates
