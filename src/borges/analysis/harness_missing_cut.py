"""Missing values of the input that a data step turns into a value of a new column.

A comparison with a missing value is False, so (skin_tone >= 0.5).astype(int) puts every unrated
player among the light-skinned: a red_cards transform did this for 21,407 dyads, and the flip it
reported was the filter that removed them (597c38e). After a data step, a new 0/1 column that
splits the known values of a numeric column at a cut, while the rows where that column is
missing all take one value, fails the step. So does a new column that takes one value on every
row where all the columns the step reads are missing, as (rater1.fillna(0) + rater2.fillna(0)) / 2
does for unrated players (597c38e), unless the option says that it imputes them.
"""

from __future__ import annotations

import ast

from borges.analysis.code_guard_missing import FILL_INTENT
from borges.analysis.models import Option


def read_names(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    return sorted(
        {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.isidentifier()
        }
    )


def imputes(option: Option) -> bool:
    return FILL_INTENT.search(f"{option.label} {option.rationale}") is not None


MISSING_CUT_SOURCE = """
    def _cut_source(flag, out, names):
        for other in names:
            source = out[other]
            if not _pd.api.types.is_numeric_dtype(source) or _pd.api.types.is_bool_dtype(source):
                continue
            gap = source.isna()
            known = source[~gap]
            if not gap.any() or known.nunique() <= 2 or flag[gap].nunique() != 1:
                continue
            ones, zeros = known[flag[~gap] == 1], known[flag[~gap] == 0]
            if ones.empty or zeros.empty:
                continue
            if ones.min() > zeros.max() or zeros.min() > ones.max():
                return other, int(gap.sum()), int(flag[gap].iloc[0])
        return None

    def _absorbed(before, out, new):
        reads = [c for c in __READS__ if c in before.columns and c in out.columns]
        if __IMPUTES__ or not reads or len(out) != len(before):
            return
        gap = before[reads].isna().all(axis=1).to_numpy()
        if not gap.any() or gap.all():
            return
        indicators = [gap.astype(int)] + [before[c].isna().to_numpy().astype(int) for c in reads]
        for name in new:
            values = out[name].to_numpy()
            if not _pd.api.types.is_numeric_dtype(out[name]) or _pd.isna(values[gap]).any():
                continue
            if any((values == flag).all() for flag in indicators):
                continue
            known = _pd.Series(values[~gap])
            varying = any(before.loc[~gap, c].nunique() > 1 for c in reads)
            constant = known.nunique() < 2
            if _pd.Series(values[gap]).nunique() != 1 or (
                constant and (not varying or values[gap][0] != 0)
            ):
                continue
            rows, verb = str(int(gap.sum())), " are" if len(reads) > 1 else " is"
            blank = (
                "out.loc[out[" + repr(reads) + "].isna().all(axis=1), " + repr(str(name))
                + "] = float('nan')"
            )
            if constant:
                raise ValueError(
                    repr(str(name)) + " has the same value in every row although "
                    + ", ".join(map(repr, reads)) + " vary: a numpy computation over a missing "
                    + "value (np.cov, np.median, np.mean) returns NaN and every comparison with "
                    + "it is False. Compute it on the complete rows only, then " + blank
                )
            raise ValueError(
                repr(str(name)) + " is " + str(values[gap][0]) + " on the " + rows
                + " rows where " + ", ".join(map(repr, reads)) + verb
                + " missing: a missing input became a value of the result (fillna, or a "
                + "comparison with a missing value, which is False). Keep the rest of the code "
                + "and add, before returning: " + blank
                + " (unless the option says that it imputes them)"
            )

    def _check_missing_cuts(before, out):
        new = [c for c in out.columns if c not in before.columns]
        names = [c for c in out.columns]
        _absorbed(before, out, new)
        for name in new:
            flag = out[name]
            if not _pd.api.types.is_numeric_dtype(flag) or flag.isna().any():
                continue
            if set(_pd.unique(flag)) != {0, 1}:
                continue
            found = _cut_source(flag, out, [c for c in names if c != name])
            if found is None:
                continue
            other, rows, value = found
            raise ValueError(
                repr(str(name)) + " cuts " + repr(str(other)) + ", but the " + str(rows)
                + " rows where " + repr(str(other)) + " is missing were all coded "
                + str(value) + ": a comparison with a missing value is False, so they joined "
                + "one group. Keep them missing, for example out[" + repr(str(name))
                + "] = (out[" + repr(str(other)) + "] >= cut).astype(float).where(out["
                + repr(str(other)) + "].notna())"
            )
"""
