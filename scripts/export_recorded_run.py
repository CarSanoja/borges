"""Export the recorded checkout run as the web app's built-in demo run."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cases" / "checkout_ab" / "recorded" / "events.jsonl"
TARGET = ROOT / "frontend" / "src" / "fixtures" / "recordedCheckout.json"
RUN_ID = "recorded-checkout"


def main() -> None:
    events = [json.loads(line) for line in SOURCE.read_text().splitlines() if line.strip()]
    for event in events:
        event["run_id"] = RUN_ID
    TARGET.write_text(json.dumps(events, separators=(",", ":")) + "\n")
    print(f"{len(events)} events -> {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
