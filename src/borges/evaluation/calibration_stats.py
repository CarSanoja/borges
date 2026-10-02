from __future__ import annotations

import math
from collections import defaultdict

Z = 1.959964


def wilson(successes: int, n: int) -> tuple[float, float, float]:
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = successes / n
    denom = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / denom
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def rate(successes: int, n: int) -> dict:
    p, low, high = wilson(successes, n)
    return {"k": successes, "n": n, "rate": p, "ci_low": low, "ci_high": high}


def summarise(rows: list[dict], scanned: dict[str, int]) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["cell"]].append(row)
    out: dict[str, dict] = {}
    for key, items in sorted(groups.items()):
        n = len(items)
        flips = [r for r in items if r["flip_found"]]
        ship = [r for r in items if r["original_verdict"] == "SHIP"]
        kinds: dict[str, int] = defaultdict(int)
        for r in flips:
            kinds[r["flip_kind"]] += 1
        out[key] = {
            "n": n,
            "scanned": scanned.get(key),
            "original_ship": rate(len(ship), n),
            "flip_any": rate(len(flips), n),
            "flip_given_ship": rate(sum(r["flip_found"] for r in ship), len(ship)),
            "flip_direction": rate(sum(r["flip_kind"] == "direction" for r in items), n),
            "flip_via_internal_traffic": rate(
                sum("internal_traffic" in r["flip_steps"] for r in items), n
            ),
            "flip_kinds": dict(kinds),
            "mean_changes_when_flip": (
                sum(r["n_changes"] for r in flips) / len(flips) if flips else None
            ),
            "mean_seconds": sum(r["seconds"] for r in items) / n,
        }
    return out
