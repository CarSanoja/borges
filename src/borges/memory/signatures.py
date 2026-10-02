from __future__ import annotations

from borges.analysis.models import AnalysisPlan, DatasetProfile, Option, Step
from borges.analysis.option_signature import normalise_text
from borges.analysis.prompts.notes import describe_column_notes
from borges.telemetry.hashing import sha256_json


def dataset_fingerprint(profile: DatasetProfile) -> str:
    columns = [
        {
            "name": c.name,
            "dtype": c.dtype,
            "n_missing": c.n_missing,
            "n_unique": c.n_unique,
            "summary": c.summary,
        }
        for c in profile.columns
    ]
    return sha256_json({"n_rows": profile.n_rows, "columns": columns})


def family_fingerprint(profile: DatasetProfile) -> str:
    return sha256_json(sorted((c.name, c.dtype) for c in profile.columns))


def option_text(option: Option) -> str:
    return f"{normalise_text(option.label)} {normalise_text(option.spec)}".strip()


def judging_context(plan: AnalysisPlan, step: Step) -> str:
    defaults = sorted(normalise_text(o.label) for o in step.options if o.is_default)
    return sha256_json(
        {
            "question": normalise_text(plan.question),
            "estimand": normalise_text(plan.estimand),
            "step_kind": step.kind,
            "defaults": defaults,
            "notes": describe_column_notes(plan.dataset),
        }
    )


def option_signature(context: str, option: Option) -> str:
    return sha256_json(
        {
            "context": context,
            "label": normalise_text(option.label),
            "spec": normalise_text(option.spec),
        }
    )


def coding_signature(plan: AnalysisPlan, step: Step, option: Option) -> str:
    index = next(i for i, s in enumerate(plan.steps) if s.id == step.id)
    earlier = [(s.id, s.kind, s.produces) for s in plan.steps[:index]]
    scale = plan.result_scale if step.kind == "model" else None
    return sha256_json(
        {
            "estimand": normalise_text(plan.estimand),
            "notes": describe_column_notes(plan.dataset),
            "step": [step.id, step.kind, step.produces],
            "earlier": earlier,
            "label": normalise_text(option.label),
            "spec": normalise_text(option.spec),
            "scale": [scale, plan.decision_rule.metric] if scale is not None else None,
        }
    )


def note_signature(column: str | None) -> str:
    return sha256_json({"note": column or ""})
