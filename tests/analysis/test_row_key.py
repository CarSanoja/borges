from __future__ import annotations

import pandas as pd

from borges.analysis.profile import profile_dataframe
from borges.analysis.row_key import row_key
from borges.armor.profile_guard import guard_profile

N = 40


def frame(**extra: list[object]) -> pd.DataFrame:
    first = ("Maria", "John", "Ana", "Omar")
    return pd.DataFrame(
        {
            "full": [f"{a} {b}ez" for a in first for b in "ABCDEFGHIJ"],
            "department": ["Sales", "Ops"] * (N // 2),
            **extra,
        }
    )


def test_a_name_as_the_only_unique_string_column_gives_no_key() -> None:
    assert row_key(profile_dataframe(frame(), "hr")) is None


def test_no_name_reaches_the_key_when_an_integer_id_exists() -> None:
    df = frame(emp_id=list(range(100, 100 + N)))
    key = row_key(profile_dataframe(df, "hr"))
    assert key == "emp_id"
    assert not set(df["full"]) & {str(v) for v in df[key]}


def test_pii_and_free_text_columns_are_never_keys() -> None:
    df = pd.DataFrame(
        {
            "mail": [f"user{i}@example.com" for i in range(N)],
            "bio": [f"wrote about topic number {i} at some length today" for i in range(N)],
            "group": ["a", "b"] * (N // 2),
        }
    )
    assert row_key(profile_dataframe(df, "d")) is None


def test_short_code_column_is_a_key_and_survives_the_guard() -> None:
    df = frame(code=[f"E{i:04d}" for i in range(N)])
    profile, _ = guard_profile(profile_dataframe(df, "hr"))
    assert row_key(profile) == "code"
