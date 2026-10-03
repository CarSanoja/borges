from __future__ import annotations

from pathlib import Path

from borges.bench.scripted_fixtures import copy_fixtures
from borges.bench.scripted_teaching import write_fixtures as write_teaching

HURRICANE_CASE = "hurricanes"


def scripted_ids() -> list[str]:
    return ["hurricane", "teachingratings"]


def install(dataset_id: str, case_dir: Path, repo_cases: Path) -> bool:
    target = case_dir / "fixtures"
    if dataset_id == "hurricane":
        source = repo_cases / HURRICANE_CASE / "fixtures"
        if not source.is_dir():
            return False
        copy_fixtures(source, target)
        return True
    if dataset_id == "teachingratings":
        write_teaching(target)
        return True
    return False
