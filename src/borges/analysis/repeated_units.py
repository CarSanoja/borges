from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

import pandas as pd
from pandas.api import types as pdt

from borges.analysis.models import RepeatedUnit

MIN_UNITS = 30
MIN_PANEL_UNITS = 5
MIN_REPEATED_SHARE = 0.2
MAX_PAIR_DUPLICATES = 0.05
ENTITY_WORDS = frozenset(
    [
        "firm",
        "company",
        "country",
        "state",
        "county",
        "city",
        "school",
        "hospital",
        "patient",
        "subject",
        "participant",
        "person",
        "user",
        "customer",
        "member",
        "household",
        "store",
        "team",
        "player",
    ]
)
TIME_WORDS = frozenset(["year", "month", "date", "wave", "period", "time", "t", "week", "day"])
WORDS = re.compile(r"[A-Za-z][a-z]*|[A-Z]+(?![a-z])")
SNAKE_ID = re.compile(r"(?:^|_)(?:id|code|num|key)$", re.IGNORECASE)
CAMEL_ID = re.compile(r"[a-z0-9](?:Id|ID|Num|Code|Short|Key)$")


NOTED_ID = re.compile(r"\bidentifier\b|\bID\b")


def looks_like_identifier(name: str) -> bool:
    return SNAKE_ID.search(name) is not None or CAMEL_ID.search(name) is not None


def noted_identifier(note: str | None) -> bool:
    return note is not None and NOTED_ID.search(note) is not None


def _words(name: str) -> set[str]:
    return {word.lower() for word in WORDS.findall(name)}


def entity_named(name: str) -> bool:
    return looks_like_identifier(name) or bool(_words(name) & ENTITY_WORDS)


def time_named(name: str) -> bool:
    return bool(_words(name) & TIME_WORDS)


def _keyable(series: pd.Series) -> bool:
    if pdt.is_bool_dtype(series):
        return False
    if pdt.is_float_dtype(series):
        values = series.dropna()
        return bool((values % 1 == 0).all())
    return pdt.is_integer_dtype(series) or not pdt.is_numeric_dtype(series)


def _same_grouping(frame: pd.DataFrame, first: str, second: str) -> bool:
    pairs = frame[[first, second]].dropna().drop_duplicates()
    return len(pairs) == pairs[first].nunique() == pairs[second].nunique()


def _repeated_share(series: pd.Series) -> float:
    present = series.dropna()
    if present.empty:
        return 0.0
    return float(present.duplicated(keep=False).sum()) / len(present)


def _panel_of(df: pd.DataFrame, unit: str, skip: set[str]) -> bool:
    """The unit crossed with a time-like column identifies rows, or nearly: a panel."""
    for column in df.columns:
        name = str(column)
        if name == unit or name in skip or not time_named(name) or pdt.is_bool_dtype(df[column]):
            continue
        pairs = df[[unit, name]].dropna()
        if pairs[name].nunique() < 2 or pairs.empty:
            continue
        if pairs.duplicated().sum() / len(pairs) <= MAX_PAIR_DUPLICATES:
            return True
    return False


def detect_repeated_units(
    df: pd.DataFrame, exclude: Iterable[str] = (), notes: Mapping[str, str] | None = None
) -> list[RepeatedUnit]:
    """Identifier columns whose values repeat across rows: the units that make rows dependent.

    A column is a repeated unit when its values are integers or text, not fractions or booleans,
    and either (a) its name reads as an identifier (ends in id, code, num, key, short, in
    snake_case or camelCase) or its column note calls it an identifier (teaching_ratings: prof,
    "instructor identifier"), it has at least 30 distinct non-missing values, and at least 20% of
    its non-missing rows belong to a value that occurs in 2 or more rows (an A/B file with 1.44
    sessions per user still has 31% of users repeating); or (b) it is a panel: its name is an
    entity (firm, country, user, or an identifier name), it has at least 5 levels, and with a
    time-like column (year, month, date, wave, period, time, t, week, day) the pair is unique or
    nearly (Grunfeld: 11 firms x 20 years). A treatment or group column with a few levels is
    neither. The outcome and the exposure, passed as
    `exclude`, are never units. A column that groups the rows exactly as an earlier detected
    column does (a player name beside its code) is the same unit and is left out. Units come
    back in column order with their distinct count and the mean rows per value.
    """
    skip = set(exclude)
    found: list[RepeatedUnit] = []
    for column in df.columns:
        name = str(column)
        named = looks_like_identifier(name) or noted_identifier((notes or {}).get(name))
        if name in skip or not (named or entity_named(name)) or not _keyable(df[column]):
            continue
        present = int(df[column].notna().sum())
        distinct = int(df[column].nunique(dropna=True))
        crowd = (
            named and distinct >= MIN_UNITS and _repeated_share(df[column]) >= MIN_REPEATED_SHARE
        )
        if not crowd and not (
            distinct >= MIN_PANEL_UNITS and present > distinct and _panel_of(df, name, skip)
        ):
            continue
        if any(_same_grouping(df, unit.name, name) for unit in found):
            continue
        found.append(
            RepeatedUnit(name=name, n_units=distinct, rows_per_unit=round(present / distinct, 2))
        )
    return found


def count_duplicate_rows(df: pd.DataFrame) -> int:
    """Rows that are exact copies of an earlier row (randhie: 11,065 of 20,190)."""
    return int(df.duplicated().sum())
