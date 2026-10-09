"""Recompute the published analysis and the 120-universe multiverse of Steegen et al. (2016).

Durante et al. (2013), Study 1, report a fertility by relationship status interaction on
religiosity, F(1, 159) = 6.46, p = .012. Steegen, Tuerlinckx, Gelman and Vanpaemel (2016,
Perspectives on Psychological Science 11(5), 702-712, Table 1) process the same raw data in
120 reasonable ways and find p < .05 in 7 of them. Run from the repository root:
    uv run --no-sync python cases/fertility_religiosity/steegen_multiverse.py
"""

from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

DATA = Path(__file__).resolve().parent / "data.parquet"
FERTILITY = {
    "F1": ((7, 14), ((17, 25),)),
    "F2": ((6, 14), ((17, 27),)),
    "F3": ((9, 17), ((18, 25),)),
    "F4": ((8, 14), ((1, 7), (15, 28))),
    "F5": ((9, 17), ((1, 8), (18, 28))),
}
RELATIONSHIP = {"R1": ({1, 2}, {3, 4}), "R2": ({1}, {2, 3, 4}), "R3": ({1}, {3, 4})}
ONSET = ("NMO1", "NMO2")
CYCLE_EXCLUSION = ("ECL1", "ECL2", "ECL3")
CERTAINTY_EXCLUSION = ("EC1", "EC2")


def consistent(onset: str, cycle_exclusion: str) -> bool:
    return not (
        (onset == "NMO1" and cycle_exclusion == "ECL3")
        or (onset == "NMO2" and cycle_exclusion == "ECL2")
    )


def universe(
    raw: pd.DataFrame,
    fertility: str,
    onset: str,
    relationship: str,
    cycle_exclusion: str,
    certainty: str,
) -> dict:
    frame = raw.copy()
    computed = (frame.StartDateofLastPeriod - frame.StartDateofPeriodBeforeLast).dt.days
    length = computed if onset == "NMO1" else frame.ReportedCycleLength
    next_onset = frame.StartDateofLastPeriod + pd.to_timedelta(length, unit="D")
    day = 28 - (next_onset - frame.DateTesting).dt.days
    high, lows = FERTILITY[fertility]
    is_low = np.any([day.between(*low) for low in lows], axis=0)
    frame["high"] = np.where(day.between(*high), 1.0, np.where(is_low, 0.0, np.nan))
    single, partnered = RELATIONSHIP[relationship]
    status = frame.Relationship
    frame["partnered"] = np.where(
        status.isin(partnered), 1.0, np.where(status.isin(single), 0.0, np.nan)
    )
    frame["religiosity"] = frame[["Rel1", "Rel2", "Rel3"]].mean(axis=1)
    if cycle_exclusion == "ECL2":
        frame = frame[computed.loc[frame.index].between(25, 35)]
    if cycle_exclusion == "ECL3":
        frame = frame[frame.ReportedCycleLength.between(25, 35)]
    if certainty == "EC2":
        frame = frame[(frame.Sure1 >= 6) & (frame.Sure2 >= 6)]
    frame = frame.dropna(subset=["high", "partnered", "religiosity"])
    fit = smf.ols("religiosity ~ high * partnered", data=frame).fit()
    row = sm.stats.anova_lm(fit, typ=2).loc["high:partnered"]
    return {
        "fertility": fertility,
        "onset": onset,
        "relationship": relationship,
        "cycle_exclusion": cycle_exclusion,
        "certainty": certainty,
        "n": len(frame),
        "interaction": fit.params["high:partnered"],
        "F": row.F,
        "p": row["PR(>F)"],
    }


def multiverse(raw: pd.DataFrame) -> pd.DataFrame:
    rows = [
        universe(raw, f, o, r, c, e)
        for f, o, r, c, e in itertools.product(
            FERTILITY, ONSET, RELATIONSHIP, CYCLE_EXCLUSION, CERTAINTY_EXCLUSION
        )
        if consistent(o, c)
    ]
    return pd.DataFrame(rows)


def main() -> None:
    table = multiverse(pd.read_parquet(DATA))
    original = table.iloc[0]
    print(
        f"published analysis (F1, NMO1, R1, no exclusions): n {original.n}, "
        f"F(1, {original.n - 4}) = {original.F:.2f}, p = {original.p:.3f}, "
        f"interaction {original.interaction:.2f}"
    )
    significant = table[table.p < 0.05]
    print(
        f"universes {len(table)}, p < .05 in {len(significant)} "
        f"({len(significant) / len(table):.1%}); positive interaction in "
        f"{int((table.interaction > 0).sum())}"
    )
    print(significant.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
