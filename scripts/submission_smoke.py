"""Exercise the packaged app through the same HTTP interface a judge uses."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


def request(base: str, path: str, body: dict | None = None) -> bytes:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers.update({"Content-Type": "application/json", "Idempotency-Key": str(uuid4())})
    with urlopen(Request(base + path, data=data, headers=headers), timeout=30) as response:
        return response.read()


def read_json(base: str, path: str, body: dict | None = None):
    return json.loads(request(base, path, body))


def check_recording(base: str, case_id: str) -> dict:
    page = request(base, f"/replay/{case_id}").decode()
    if 'type="module"' not in page:
        raise ValueError(f"{case_id}: the built frontend was not served")
    raw = request(base, f"/api/cases/{case_id}/recording?source=live&speed=10000")
    events = [
        json.loads(line[6:]) for line in raw.decode().splitlines() if line.startswith("data: ")
    ]
    if not events or events[0]["type"] != "run.started" or events[-1]["type"] != "run.finished":
        raise ValueError(f"{case_id}: incomplete recorded event stream")
    return {"case": case_id, "events": len(events), "status": "pass"}


def check_run(base: str, llm: str, timeout: float) -> dict:
    started = time.monotonic()
    created = read_json(base, "/api/runs", {"case_id": "checkout_ab", "llm": llm})
    run_id = created["run_id"]
    create_seconds = time.monotonic() - started
    while time.monotonic() - started < timeout:
        snapshot = read_json(base, f"/api/runs/{run_id}")
        if snapshot["status"] not in ("queued", "running"):
            break
        time.sleep(0.5)
    else:
        raise ValueError(f"{run_id}: did not finish within {timeout:g}s")
    if snapshot["status"] != "completed":
        raise ValueError(f"{run_id}: run ended as {snapshot['status']}")
    report = snapshot.get("report")
    if not report or not report.get("narrative"):
        raise ValueError(f"{run_id}: no final narrative")
    flip = snapshot.get("flip")
    if llm == "scripted" and not (
        flip
        and flip["baseline_verdict"] == "SHIP"
        and flip["flipped_verdict"] == "DON'T SHIP"
        and flip["reproduced"]
    ):
        raise ValueError(f"{run_id}: expected verified scripted flip was not produced")
    if flip:
        detail = read_json(base, f"/api/runs/{run_id}/universes/{flip['universe_id']}")
        if not detail["steps"] or not all(step["option"].get("code") for step in detail["steps"]):
            raise ValueError(f"{run_id}: universe detail did not include its executed code")
    return {
        "run_id": run_id,
        "llm": llm,
        "status": "pass",
        "create_seconds": round(create_seconds, 3),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "flip_reproduced": flip.get("reproduced") if flip else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:18481")
    parser.add_argument("--run-scripted", action="store_true")
    parser.add_argument(
        "--run-live", action="store_true", help="Makes billable Token Factory calls"
    )
    parser.add_argument("--require-live", action="store_true")
    parser.add_argument("--max-cost-usd", type=float, default=0.50)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    base = args.url.rstrip("/")
    result: dict = {"checked_at": datetime.now(UTC).isoformat(), "url": base, "status": "fail"}
    try:
        health = read_json(base, "/api/health")
        if health.get("status") != "ok":
            raise ValueError("health endpoint did not report ok")
        result["health"] = health
        cards = read_json(base, "/api/cases")
        if not cards:
            raise ValueError("no curated cases available")
        result["recordings"] = [check_recording(base, card["id"]) for card in cards]
        if args.run_scripted:
            result["scripted"] = check_run(base, "scripted", args.timeout)
        if (args.require_live or args.run_live) and not health.get("llm_live_available"):
            raise ValueError(f"live mode unavailable: {health.get('live_unavailable_reason')}")
        if args.run_live:
            cap = health.get("max_cost_per_live_run_usd")
            if not isinstance(cap, (int, float)) or not 0 < cap <= args.max_cost_usd:
                raise ValueError("server run cap is missing or exceeds --max-cost-usd")
            result["live"] = check_run(base, "nebius", args.timeout)
        result["status"] = "pass"
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
        result["error"] = str(exc)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
    print(rendered, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
