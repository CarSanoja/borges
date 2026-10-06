from __future__ import annotations

import re
from pathlib import Path

import pyarrow.parquet as pq

from borges.cases.live_summary import LIVE_FOLDER, RecordingSource, summarize_live
from borges.cases.models import CaseCard, CaseSpec
from borges.cases.recording_stamp import RecordingStamp, read_stamp
from borges.runs.events import Event

LIVE_ONLY_MESSAGE = (
    "Case '{case_id}' is live-only: it has no scripted fixtures and no recording. "
    "Run it with llm=nebius and NEBIUS_API_KEY."
)
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")


class CaseRegistry:
    """Curated cases on disk: `<cases_dir>/<id>/{case.json,data.parquet,fixtures/,recorded/}`."""

    def __init__(self, cases_dir: Path) -> None:
        self.cases_dir = Path(cases_dir)

    def _dir(self, case_id: str) -> Path:
        directory = self.cases_dir / case_id
        if not _SAFE_ID.fullmatch(case_id) or not (directory / "case.json").is_file():
            raise KeyError(case_id)
        return directory

    def get(self, case_id: str) -> CaseSpec:
        directory = self._dir(case_id)
        spec = CaseSpec.model_validate_json((directory / "case.json").read_text(encoding="utf-8"))
        return spec.model_copy(update={"id": case_id})

    def data_bytes(self, case_id: str) -> bytes:
        return (self._dir(case_id) / self.get(case_id).dataset_file).read_bytes()

    def fixtures_dir(self, case_id: str) -> Path | None:
        directory = self._dir(case_id)
        if self.get(case_id).live_only:
            return None
        return directory / "fixtures"

    def require_scripted(self, case_id: str) -> None:
        if self.get(case_id).live_only:
            raise ValueError(LIVE_ONLY_MESSAGE.format(case_id=case_id))

    def _recording_path(self, case_id: str, source: RecordingSource = "scripted") -> Path:
        folder = LIVE_FOLDER if source == "live" else "recorded"
        return self._dir(case_id) / folder / "events.jsonl"

    def recording_dir(self, case_id: str, source: RecordingSource = "scripted") -> Path:
        return self._recording_path(case_id, source).parent

    def has_spans(self, case_id: str, source: RecordingSource = "scripted") -> bool:
        spans = self.recording_dir(case_id, source) / "spans.jsonl"
        return spans.is_file() and spans.stat().st_size > 0

    def recording(self, case_id: str, source: RecordingSource = "scripted") -> list[Event] | None:
        if source not in ("scripted", "live"):
            raise ValueError(f"unknown recording source '{source}'")
        path = self._recording_path(case_id, source)
        if not path.is_file():
            return None
        lines = path.read_text(encoding="utf-8").splitlines()
        return [Event.model_validate_json(line) for line in lines if line.strip()]

    def card(self, case_id: str) -> CaseCard:
        spec = self.get(case_id)
        dataset = self._dir(case_id) / spec.dataset_file
        n_rows = pq.ParquetFile(dataset).metadata.num_rows
        fields = spec.model_dump(
            include=set(CaseCard.model_fields)
            - {"n_rows", "has_recording", "has_scripted_recording", "has_live_recording"}
        )
        live = self.recording(case_id, "live")
        traced = [
            source
            for source, present in (("live", bool(live)), ("scripted", True))
            if present and self.has_spans(case_id, source)
        ]
        stamps: dict[str, RecordingStamp] = {}
        for source in ("scripted", "live"):
            stamp = read_stamp(self.recording_dir(case_id, source))
            if stamp is not None:
                stamps[source] = stamp
        scripted_present = self._recording_path(case_id).is_file()
        live_present = bool(live)
        return CaseCard(
            **fields,
            recording_meta=stamps,
            traced_sources=traced,
            n_rows=n_rows,
            has_recording=scripted_present or live_present,
            has_scripted_recording=scripted_present,
            has_live_recording=live_present,
            live_recording=summarize_live(live) if live else None,
        )

    def list(self) -> list[CaseCard]:
        if not self.cases_dir.is_dir():
            return []
        ids = sorted(p.name for p in self.cases_dir.iterdir() if (p / "case.json").is_file())
        return [self.card(case_id) for case_id in ids]
