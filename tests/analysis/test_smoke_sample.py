from __future__ import annotations

import numpy as np
import pandas as pd

from borges.analysis.smoke_sample import group_column, sample_frame


def sessions(users: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    per_user = rng.integers(1, 5, size=users)
    user = np.repeat(np.arange(users), per_user)
    return pd.DataFrame(
        {
            "session_id": np.arange(user.size),
            "user_id": user,
            "converted": rng.integers(0, 2, size=user.size),
        }
    )


def test_the_repeating_id_is_the_group() -> None:
    frame = sessions()
    assert group_column(frame) == "user_id"
    assert group_column(frame.drop(columns=["user_id"])) is None


def test_a_group_sample_keeps_every_session_of_a_sampled_user() -> None:
    frame = sessions()
    sample = sample_frame(frame, 500, 7)
    assert 500 <= len(sample) <= 504
    full = frame.groupby("user_id").size()
    kept = sample.groupby("user_id").size()
    assert (kept == full.loc[kept.index]).all()
    rates = sample.groupby("user_id")["converted"].sum()
    assert rates.max() > 1
    assert sample.equals(sample_frame(frame, 500, 7))


def test_without_a_repeating_id_rows_are_sampled() -> None:
    frame = sessions().drop(columns=["user_id"])
    assert len(sample_frame(frame, 300, 7)) == 300


def test_a_rare_level_of_a_text_column_is_always_in_the_sample() -> None:
    frame = sessions().drop(columns=["user_id"])
    frame["default"] = "no"
    frame.loc[frame.index[-3:], "default"] = "yes"
    frame["flag"] = frame["session_id"] == 5
    sample = sample_frame(frame, 300, 7)
    assert set(sample["default"]) == {"no", "yes"} and set(sample["flag"]) == {True, False}
    assert int(sample["default"].eq("yes").sum()) == 3
    assert 300 < len(sample) <= 304


def test_a_rare_level_brings_its_whole_group() -> None:
    frame = sessions()
    frame["plan"] = "free"
    frame.loc[frame["user_id"] == 1999, "plan"] = "pro"
    sample = sample_frame(frame, 500, 7)
    assert "pro" in set(sample["plan"])
    assert (sample["user_id"] == 1999).sum() == (frame["user_id"] == 1999).sum()


def bleeds(patients: int = 3000) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    return pd.DataFrame(
        {
            "age": rng.integers(40, 95, size=patients),
            "new_drug": rng.integers(0, 2, size=patients),
            "bleed": (rng.random(patients) < 0.02).astype(int),
        }
    )


def test_a_rare_outcome_has_enough_events_in_the_sample() -> None:
    frame = bleeds()
    assert frame["bleed"].sum() >= 20
    sample = sample_frame(frame, 200, 7)
    assert int(sample["bleed"].sum()) >= 20
    assert len(sample) <= 220
    assert sample_frame(frame, 200, 7).index.equals(sample.index)


def test_a_rare_outcome_with_few_events_keeps_all_of_them() -> None:
    frame = bleeds()
    frame.loc[frame.index[frame["bleed"].eq(1)][5:], "bleed"] = 0
    assert int(sample_frame(frame, 200, 7)["bleed"].sum()) == 5


def test_a_group_sample_adds_whole_groups_for_a_rare_value() -> None:
    frame = sessions()
    frame["converted"] = 0
    frame.loc[frame.index[::97], "converted"] = 1
    sample = sample_frame(frame, 500, 7)
    assert int(sample["converted"].sum()) >= 20
    sampled = set(sample["user_id"])
    assert len(sample) == int(frame["user_id"].isin(sampled).sum())
