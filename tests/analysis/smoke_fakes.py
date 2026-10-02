from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from borges.sandbox.backend import Checkpoint, ExecResult

RESULT = {"estimate": 0.5, "ci_low": 0.1, "ci_high": 0.9, "p_value": 0.01, "n": 100}


def probe(values: list[float]) -> dict[str, float]:
    return {str(i): v for i, v in enumerate(values)}


def effects(
    column: str | None = None,
    values: list[float] | None = None,
    rows: tuple[int, int] = (100, 100),
    dropped: dict[str, dict[str, int]] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "rows_before": rows[0],
        "rows_after": rows[1],
        "added": [column] if column else [],
        "changed": [],
        "columns": {},
        "ctx_added": {},
    }
    if column and values is not None:
        out["columns"][column] = {
            "mean": sum(values) / len(values),
            "sd": 1.0,
            "min": min(values),
            "max": max(values),
            "n_missing": 0,
            "probe": probe(values),
        }
    if dropped:
        out["dropped_rows_by"] = dropped
    return out


def stdout(step_id: str, option_id: str, payload: dict[str, Any] | None, model: bool) -> str:
    trace = {"step_id": step_id, "option_id": option_id, "rows_before": 100, "rows_after": 100}
    if payload is not None:
        trace["effects"] = payload
    lines = ["BORGES_TRACE " + json.dumps(trace)]
    if model:
        lines.append("BORGES_RESULT " + json.dumps(RESULT))
    return "\n".join(lines) + "\n"


@dataclass
class ScriptBackend:
    script: list[tuple[str, dict[str, Any] | None]]
    name: str = "script"
    runs: list[str] = field(default_factory=list)
    counter: int = 0

    async def root(self, files: Mapping[str, bytes]) -> Checkpoint:
        return Checkpoint("root", None, self.name)

    async def run(
        self,
        parent: Checkpoint,
        command: Sequence[str],
        files: Mapping[str, bytes] | None = None,
        timeout_s: float = 120.0,
    ) -> ExecResult:
        path, source = next(iter((files or {}).items()))
        step_id, option_id = path.split("/")[-1][:-3].split("__")
        self.runs.append(f"{step_id}.{option_id}")
        payload = next((p for marker, p in self.script if marker in source.decode()), None)
        self.counter += 1
        checkpoint = Checkpoint(f"c{self.counter}", parent.id, self.name)
        out = stdout(step_id, option_id, payload, step_id.startswith("m"))
        return ExecResult(checkpoint, 0, out, "", 0.0)

    async def read_file(self, checkpoint: Checkpoint, path: str) -> bytes:
        return b""

    async def close(self) -> None:
        return None
