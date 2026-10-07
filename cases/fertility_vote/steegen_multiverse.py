"""Steegen et al.'s (2016) multiverse for Durante et al.'s (2013) Study 2 vote, from the raw data.

A Python port of their R code (osf.io/zj68b, "multiverse analysis steegen et al 2016_osf.R",
analysis 5): three next-onset rules, five fertility windows, three relationship codings, three
cycle-length exclusions and two certainty exclusions, 210 valid combinations, a logistic regression
of Vote on fertility, relationship status and their product. As in R, a row whose exclusion
criterion is missing is dropped, the cycle day is clipped to 1-28, and under the first next-onset
rule WorkerID 15 and 16 take the cycle days 11 and 18 of the original authors' file.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

DATA = Path(__file__).resolve().parent / "data.parquet"
HIGH = [(7, 14), (6, 14), (9, 17), (8, 14), (9, 17)]
LOW = [((17, 25),), ((17, 27),), ((18, 25),), ((1, 7), (15, 28)), ((1, 8), (18, 28))]
NAMES = ("NMO", "F", "R", "ECL", "EC")


def processed(raw: pd.DataFrame, nmo: int, f: int, r: int, ecl: int, ec: int) -> pd.DataFrame:
    frame = raw.copy()
    computed = (frame.StartDateofLastPeriod - frame.StartDateofPeriodBeforeLast).dt.days
    if nmo == 0:
        onset = frame.StartDateofLastPeriod + pd.to_timedelta(computed, unit="D")
    elif nmo == 1:
        onset = frame.StartDateofLastPeriod + pd.to_timedelta(frame.ReportedCycleLength, unit="D")
    else:
        onset = frame.StartDateNext
    day = (28 - (onset - frame.DateTesting).dt.days).clip(1, 28)
    if nmo == 0:
        day = day.where(frame.WorkerID != 15, 11).where(frame.WorkerID != 16, 18)
    is_low = np.any([day.between(*low) for low in LOW[f]], axis=0)
    frame["high"] = np.where(day.between(*HIGH[f]), 1.0, np.where(is_low, 0.0, np.nan))
    if r == 0:
        frame["committed"] = np.where(frame.Relationship >= 3, 1.0, 0.0)
    elif r == 1:
        frame["committed"] = np.where(frame.Relationship >= 2, 1.0, 0.0)
    else:
        frame["committed"] = frame.Relationship.map({1: 0.0, 3: 1.0, 4: 1.0})
    if ecl == 1:
        frame = frame[computed.loc[frame.index].between(25, 35)]
    elif ecl == 2:
        frame = frame[frame.ReportedCycleLength.between(25, 35)]
    if ec == 1:
        frame = frame[(frame.Sure1 >= 6) & (frame.Sure2 >= 6)]
    return frame.dropna(subset=["high", "committed", "Vote"])


def interaction(frame: pd.DataFrame) -> tuple[float, float, int]:
    fit = smf.logit("Vote ~ high * committed", data=frame).fit(disp=0)
    return float(fit.params["high:committed"]), float(fit.pvalues["high:committed"]), int(fit.nobs)


def multiverse(raw: pd.DataFrame) -> list[tuple[tuple[int, ...], float, float, int]]:
    rows = []
    for combo in itertools.product(range(3), range(5), range(3), range(3), range(2)):
        nmo, _, _, ecl, _ = combo
        if (nmo == 0 and ecl == 2) or (nmo == 1 and ecl == 1):
            continue
        rows.append((combo, *interaction(processed(raw, *combo))))
    return rows


def label(combo: tuple[int, ...]) -> str:
    return ", ".join(f"{name}{value + 1}" for name, value in zip(NAMES, combo, strict=True))


def main() -> None:
    rows = multiverse(pd.read_parquet(DATA))
    published = rows[0]
    significant = sum(p < 0.05 for _, _, p, _ in rows)
    print(
        f"published analysis ({label(published[0])}): interaction {published[1]:+.4f}, "
        f"p {published[2]:.4f}, n {published[3]}"
    )
    print(f"p < .05 in {significant} of {len(rows)} combinations")
    for combo, estimate, p, n in rows:
        if sum(value != 0 for value in combo) == 1:
            mark = "flips" if p >= 0.05 else "holds"
            print(f"  {label(combo)}: {estimate:+.4f}, p {p:.4f}, n {n} ({mark})")


if __name__ == "__main__":
    main()
