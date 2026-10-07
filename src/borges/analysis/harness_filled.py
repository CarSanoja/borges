"""A column the step must produce that it leaves missing in almost every row it keeps.

fertility_vote on 7 October, run 38: the cycle-day filter was told to produce cycle_day, kept the
computed days in a local variable and wrote the column only for two rows picked by position, so
cycle_day was missing in 300 of 301 rows and the fertility indicator was all zeros. The harness
checked that the column existed. However the code is written, a produced column missing in 95% of
the rows the step returns, when the step did not receive it that way, fails the step that made it.
"""

from __future__ import annotations

FILLED_MIN_ROWS = 20
FILLED_SHARE = 0.95

FILLED_SOURCE = """
    def _check_filled(name, out, df):
        if name not in out.columns or len(out) < __FILLED_MIN_ROWS__:
            return
        missing = int(out[name].isna().sum())
        if missing < __FILLED_SHARE__ * len(out):
            return
        if name in df.columns and df[name].isna().sum() >= __FILLED_SHARE__ * len(df):
            return
        raise ValueError(
            "this step must produce " + repr(name) + " with a value for the rows it keeps, but it"
            + " is missing in " + str(missing) + " of " + str(len(out)) + " rows: compute it for"
            + " every row and assign the whole column; values the analysis sets by hand for some"
            + " rows go on top of the computed column, after it is assigned"
        )
""".replace("__FILLED_MIN_ROWS__", str(FILLED_MIN_ROWS)).replace(
    "__FILLED_SHARE__", str(FILLED_SHARE)
)
