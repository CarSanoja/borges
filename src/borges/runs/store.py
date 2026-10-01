from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from borges.runs.events import Event
from borges.runs.models import RunSnapshot, RunSummary
from borges.runs.state import fold

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class RunStore:
    """Append-only run storage: `<runs_dir>/<run_id>/{meta.json,events.jsonl}`."""

    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = Path(runs_dir)

    def _dir(self, run_id: str) -> Path:
        if not _SAFE_ID.match(run_id):
            raise KeyError(run_id)
        return self.runs_dir / run_id

    def exists(self, run_id: str) -> bool:
        try:
            return (self._dir(run_id) / "meta.json").is_file()
        except KeyError:
            return False

    def create(self, run_id: str, meta: dict[str, Any]) -> None:
        directory = self._dir(run_id)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "events.jsonl").touch()
        self._write_meta(run_id, {**meta, "run_id": run_id})

    def _write_meta(self, run_id: str, meta: dict[str, Any]) -> None:
        target = self._dir(run_id) / "meta.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
        temporary.replace(target)

    def meta(self, run_id: str) -> dict[str, Any]:
        if not self.exists(run_id):
            raise KeyError(run_id)
        return json.loads((self._dir(run_id) / "meta.json").read_text(encoding="utf-8"))

    def update_meta(self, run_id: str, **fields: Any) -> dict[str, Any]:
        meta = {**self.meta(run_id), **fields}
        self._write_meta(run_id, meta)
        return meta

    def append(self, event: Event) -> None:
        if not self.exists(event.run_id):
            raise KeyError(event.run_id)
        line = event.model_dump_json()
        with (self._dir(event.run_id) / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()

    def events(self, run_id: str) -> list[Event]:
        if not self.exists(run_id):
            raise KeyError(run_id)
        path = self._dir(run_id) / "events.jsonl"
        if not path.is_file():
            return []
        events: list[Event] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                events.append(Event.model_validate_json(line))
            except ValidationError:
                continue
        return events

    def snapshot(self, run_id: str) -> RunSnapshot:
        return fold(self.events(run_id), run_id)

    def list_runs(self) -> list[RunSummary]:
        if not self.runs_dir.is_dir():
            return []
        summaries: list[RunSummary] = []
        for directory in self.runs_dir.iterdir():
            if not self.exists(directory.name):
                continue
            try:
                summaries.append(RunSummary.model_validate(self.meta(directory.name)))
            except (ValidationError, json.JSONDecodeError):
                continue
        return sorted(summaries, key=lambda s: s.created_at, reverse=True)
