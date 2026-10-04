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
    assert 300 < len(sample) <= 302


def test_a_rare_level_brings_its_whole_group() -> None:
    frame = sessions()
    frame["plan"] = "free"
    frame.loc[frame["user_id"] == 1999, "plan"] = "pro"
    sample = sample_frame(frame, 500, 7)
    assert "pro" in set(sample["plan"])
    assert (sample["user_id"] == 1999).sum() == (frame["user_id"] == 1999).sum()
