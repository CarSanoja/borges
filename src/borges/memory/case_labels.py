"""Curated case titles for the dataset fingerprints that key the memory.

Memories are keyed by a fingerprint of the dataset profile, which the memory page showed as a bare
hash. The public demo memory holds curated cases only, so each fingerprint is matched to the case
whose data has it, computed once per process.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from borges.analysis.profile import profile_dataframe
from borges.cases.registry import CaseRegistry
from borges.memory.signatures import dataset_fingerprint
from borges.runs.pipeline_data import load_dataframe


@lru_cache(maxsize=4)
def curated_labels(cases_dir: str) -> dict[str, str]:
    root = Path(cases_dir)
    if not root.is_dir():
        return {}
    registry = CaseRegistry(root)
    titles: dict[str, list[str]] = {}
    for case_id in sorted(p.name for p in root.iterdir() if (p / "case.json").is_file()):
        try:
            frame = load_dataframe(registry.data_bytes(case_id))
        except (OSError, KeyError, ValueError):
            continue
        fingerprint = dataset_fingerprint(profile_dataframe(frame, case_id))
        titles.setdefault(fingerprint, []).append(registry.get(case_id).title)
    return {fingerprint: " / ".join(names) for fingerprint, names in titles.items()}


def with_case_labels(summary: dict[str, Any], cases_dir: Path) -> dict[str, Any]:
    datasets = summary.get("datasets") or []
    if not datasets:
        return summary
    labels = curated_labels(str(cases_dir))
    labelled = [{**row, "label": labels.get(str(row["dataset"]))} for row in datasets]
    return {**summary, "datasets": labelled}
