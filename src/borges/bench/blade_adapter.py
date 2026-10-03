from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from borges.bench.blade_rules import RULES, BladeRule
from borges.bench.blade_source import BladeDataset, read_frame
from borges.cases.models import CaseSpec
from borges.runs.models import RunRequest

SAMPLE_SEED = 20240816
NOTE_CHARS = 300


@dataclass(frozen=True)
class AdaptedCase:
    case_id: str
    case_dir: Path
    rule: BladeRule
    n_rows: int
    source_rows: int
    note: str | None


def case_id_for(dataset_id: str) -> str:
    return f"blade_{dataset_id}"


def sampling_note(source_rows: int, kept: int) -> str | None:
    if kept >= source_rows:
        return None
    return f"sampled {kept} of {source_rows} rows (seed {SAMPLE_SEED}) to bound sandbox time"


def build_case(
    dataset: BladeDataset, cases_dir: Path, max_rows: int, max_universes: int
) -> AdaptedCase:
    rule = RULES[dataset.id]
    frame = read_frame(dataset)
    source_rows = len(frame)
    if source_rows > max_rows:
        frame = frame.sample(n=max_rows, random_state=SAMPLE_SEED).sort_index()
    case_id = case_id_for(dataset.id)
    case_dir = cases_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(case_dir / "data.parquet", index=False)
    notes = {
        name: text[:NOTE_CHARS]
        for name, text in dataset.columns.items()
        if text and name in frame.columns
    }
    spec = CaseSpec(
        id=case_id,
        title=f"BLADE {dataset.id}",
        subtitle="BLADE benchmark dataset with a decision rule written from its research question",
        question=rule.question,
        decision_rule=rule.decision_rule(),
        dataset_name=dataset.id,
        max_universes=max_universes,
        column_notes=notes,
    )
    (case_dir / "case.json").write_text(spec.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return AdaptedCase(
        case_id=case_id,
        case_dir=case_dir,
        rule=rule,
        n_rows=len(frame),
        source_rows=source_rows,
        note=sampling_note(source_rows, len(frame)),
    )


def to_request(adapted: AdaptedCase, llm: str, max_universes: int) -> RunRequest:
    return RunRequest(
        case_id=adapted.case_id,
        llm=llm,
        backend="local",
        max_universes=max_universes,
    )
