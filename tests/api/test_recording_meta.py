from __future__ import annotations

from pathlib import Path

from borges.cases.recording_stamp import RecordingStamp, write_stamp
from tests.api.test_recorded_trace import get, make_app


async def test_card_serves_recording_json_per_source(tmp_path: Path) -> None:
    app = make_app(tmp_path, traced=False)
    live = tmp_path / "cases" / "checkout_ab" / "recorded-live"
    stamp = RecordingStamp(commit="abc1234", backend="local", recorded_at="2026-10-02T11:11:56Z")
    write_stamp(live, stamp)
    card = (await get(app, "/api/cases/checkout_ab")).json()
    assert card["recording_meta"]["live"]["commit"] == "abc1234"
    assert card["recording_meta"]["live"]["backend"] == "local"
    assert "scripted" not in card["recording_meta"]


async def test_card_without_recording_json_has_empty_meta(tmp_path: Path) -> None:
    card = (await get(make_app(tmp_path, traced=False), "/api/cases/checkout_ab")).json()
    assert card["recording_meta"] == {}
