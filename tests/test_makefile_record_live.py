from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ("checkout_ab", "red_cards", "marp_religiosity", "marp_norms", "bank_marketing_calls")


def dry_run(target: str) -> list[str]:
    done = subprocess.run(
        ["make", "-n", target], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return done.stdout.splitlines()


def test_record_live_records_all_five_cases_live_after_smoke() -> None:
    lines = dry_run("record-live")
    assert any("live_smoke.py" in line for line in lines)
    recorded = [line for line in lines if "record-demo" in line]
    assert len(recorded) == len(CASES)
    for case in CASES:
        assert any(f"--case {case} " in line and "--llm nebius" in line for line in recorded)
    smoke_at = next(i for i, line in enumerate(lines) if "live_smoke.py" in line)
    assert smoke_at < lines.index(recorded[0])


def test_record_live_keeps_the_per_run_cap_and_spares_scripted_recordings() -> None:
    text = (ROOT / "Makefile").read_text()
    assert "record-live: export BORGES_RUN_CAP_USD ?= 0.50" in text
    lines = dry_run("record-live")
    assert not any("export_recorded_run" in line for line in lines)
    assert not any("--llm scripted" in line for line in lines)
