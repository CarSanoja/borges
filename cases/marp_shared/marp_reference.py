from __future__ import annotations

import pandas as pd
from marp_data import CODING_CSV, CODING_URL, TEAMS_CSV, TEAMS_URL, fetch_cached

from borges.cases.models import ReferenceEstimate

LABEL_LIMIT = 70


def load_teams() -> pd.DataFrame:
    return pd.read_csv(fetch_cached(TEAMS_URL, TEAMS_CSV))


def load_coding() -> pd.DataFrame:
    return pd.read_csv(fetch_cached(CODING_URL, CODING_CSV)).fillna("")


def team_approach(text: object) -> str:
    flat = " ".join(str(text).split())
    return flat if len(flat) <= LABEL_LIMIT else flat[: LABEL_LIMIT - 3].rstrip() + "..."


def reference(rq: int) -> list[ReferenceEstimate]:
    teams = load_teams()
    cols = [f"Standardized_ES_{rq}", f"lower_CI_{rq}", f"upper_CI_{rq}"]
    kept = teams.dropna(subset=cols)
    return [
        ReferenceEstimate(
            label=f"Team {int(row.Team)}: {team_approach(row.AnalyticalApproach)}",
            estimate=float(row[cols[0]]),
            ci_low=float(row[cols[1]]),
            ci_high=float(row[cols[2]]),
            significant=bool(row[cols[1]] > 0),
        )
        for _, row in kept.iterrows()
    ]


def team_summary(rq: int) -> dict[str, float]:
    refs = reference(rq)
    estimates = sorted(r.estimate for r in refs)
    n = len(estimates)
    median = estimates[n // 2] if n % 2 else (estimates[n // 2 - 1] + estimates[n // 2]) / 2
    return {
        "n_teams": n,
        "n_significant": sum(1 for r in refs if r.significant),
        "min": estimates[0],
        "max": estimates[-1],
        "median": median,
    }
