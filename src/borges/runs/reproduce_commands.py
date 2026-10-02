from __future__ import annotations

from typing import Literal

from borges.runs.models import UniverseDetail

ReproduceKind = Literal["case", "script"]
DATA_PLACEHOLDER = "path/to/data.parquet"


class ReproducibleUniverse(UniverseDetail):
    reproduce_kind: ReproduceKind = "script"
    script_url: str | None = None
    script_filename: str | None = None


def case_command(case_id: str, universe_id: str, source: str = "scripted") -> str:
    base = f"uv run borges reproduce --case {case_id} --universe {universe_id}"
    return f"{base} --source live" if source == "live" else base


def script_filename(run_id: str, universe_id: str) -> str:
    return f"borges_{run_id}_{universe_id}.py"


def script_command(run_id: str, universe_id: str) -> str:
    return f"python {script_filename(run_id, universe_id)} --data {DATA_PLACEHOLDER}"


def script_url(run_id: str, universe_id: str) -> str:
    return f"/api/runs/{run_id}/universes/{universe_id}/script"


def with_reproduce(
    detail: UniverseDetail, run_id: str, recorded_case: str | None, source: str = "scripted"
) -> ReproducibleUniverse:
    universe_id = detail.universe.id
    base = detail.model_dump(include=set(UniverseDetail.model_fields) - {"reproduce_command"})
    if recorded_case is not None:
        return ReproducibleUniverse(
            **base,
            reproduce_command=case_command(recorded_case, universe_id, source),
            reproduce_kind="case",
            script_url=script_url(run_id, universe_id),
            script_filename=script_filename(run_id, universe_id),
        )
    return ReproducibleUniverse(
        **base,
        reproduce_command=script_command(run_id, universe_id),
        reproduce_kind="script",
        script_url=script_url(run_id, universe_id),
        script_filename=script_filename(run_id, universe_id),
    )
