from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from borges.analysis.profile import blind_profile, profile_dataframe
from borges.analysis.repeated_units import (
    count_duplicate_rows,
    detect_repeated_units,
    looks_like_identifier,
)

RED_CARDS = Path(__file__).resolve().parents[2] / "cases" / "red_cards" / "data.parquet"


def frame(rows: int = 600, **columns: object) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    base: dict[str, object] = {"value": rng.normal(size=rows)}
    return pd.DataFrame({**base, **columns})


def test_identifier_names_in_snake_and_camel_case_are_recognised() -> None:
    for name in ("user_id", "playerShort", "refNum", "site_code", "sessionKey", "id"):
        assert looks_like_identifier(name), name
    for name in ("games", "refCountry", "valid", "height", "identity"):
        assert not looks_like_identifier(name), name


def test_an_id_column_whose_values_repeat_is_a_repeated_unit() -> None:
    users = np.repeat(np.arange(60), 10)
    units = detect_repeated_units(frame(user_id=users))
    assert [(u.name, u.n_units, u.rows_per_unit) for u in units] == [("user_id", 60, 10.0)]


def test_a_column_with_few_distinct_values_is_not_a_unit() -> None:
    assert detect_repeated_units(frame(user_id=np.repeat(np.arange(29), 21)[:600])) == []


def test_a_column_that_does_not_repeat_is_not_a_unit() -> None:
    assert detect_repeated_units(frame(row_id=np.arange(600))) == []
    thin = np.arange(600) % 590
    assert detect_repeated_units(frame(row_id=thin)) == []


def test_rows_per_unit_of_exactly_two_counts() -> None:
    assert [
        u.n_units for u in detect_repeated_units(frame(pair_id=np.repeat(np.arange(300), 2)))
    ] == [300]


def test_only_columns_named_like_identifiers_count() -> None:
    assert detect_repeated_units(frame(group=np.repeat(np.arange(60), 10))) == []


def test_floats_with_fractions_and_booleans_are_not_units() -> None:
    fractional = np.repeat(np.arange(60) + 0.5, 10)
    assert detect_repeated_units(frame(user_id=fractional)) == []
    assert detect_repeated_units(frame(flag_id=np.arange(600) % 2 == 0)) == []


def test_integer_valued_floats_and_text_are_units() -> None:
    codes = np.repeat(np.arange(60), 10)
    units = detect_repeated_units(
        frame(user_id=codes.astype(float), site_code=[f"s{c}" for c in codes])
    )
    assert [u.name for u in units] == ["user_id"]


def test_the_outcome_and_the_exposure_are_never_units() -> None:
    data = frame(user_id=np.repeat(np.arange(60), 10), arm_code=np.arange(600) % 40)
    assert detect_repeated_units(data, exclude={"user_id"}) == detect_repeated_units(
        data.drop(columns="user_id")
    )
    assert [u.name for u in detect_repeated_units(data, exclude={"arm_code"})] == ["user_id"]


def test_missing_values_are_not_a_unit_and_do_not_count_as_rows() -> None:
    users = pd.Series(np.repeat(np.arange(60), 10), dtype="float")
    users[:300] = np.nan
    units = detect_repeated_units(frame(user_id=users))
    assert [(u.n_units, u.rows_per_unit) for u in units] == [(30, 10.0)]


def test_a_second_column_that_groups_the_rows_the_same_way_is_the_same_unit() -> None:
    codes = np.repeat(np.arange(60), 10)
    data = frame(player_id=codes, player_code=codes * 7 + 3, team_id=codes // 2 % 40)
    names = [u.name for u in detect_repeated_units(data)]
    assert names == ["player_id", "team_id"]


def test_the_red_cards_data_repeats_players_and_referees() -> None:
    subset = pd.read_parquet(RED_CARDS).head(20000)
    units = {u.name: u for u in detect_repeated_units(subset)}
    assert set(units) == {"playerShort", "refNum"}
    assert units["playerShort"].rows_per_unit >= 2 and units["refNum"].n_units >= 30
    full = pd.read_parquet(RED_CARDS)
    named = {u.name: u.n_units for u in detect_repeated_units(full)}
    assert named == {"playerShort": 2053, "refNum": 3147}


def test_the_profile_records_the_repeated_units_with_their_counts() -> None:
    data = frame(user_id=np.repeat(np.arange(60), 10))
    profile = profile_dataframe(data, "visits")
    assert [(u.name, u.n_units, u.rows_per_unit) for u in profile.repeated_units] == [
        ("user_id", 60, 10.0)
    ]
    assert blind_profile(profile).repeated_units == profile.repeated_units
    assert profile_dataframe(frame(), "visits").repeated_units == []


CASES = Path(__file__).resolve().parents[2] / "cases"


def test_a_column_its_note_calls_an_identifier_is_a_unit() -> None:
    import json

    case = json.loads((CASES / "teaching_ratings" / "case.json").read_text())
    data = pd.read_parquet(CASES / "teaching_ratings" / "data.parquet")
    assert detect_repeated_units(data) == []
    [unit] = detect_repeated_units(data, notes=case["column_notes"])
    assert (unit.name, unit.n_units) == ("prof", 94)


def test_a_noted_identifier_with_one_row_each_is_not_a_unit() -> None:
    import json

    case = json.loads((CASES / "fertility_religiosity" / "case.json").read_text())
    data = pd.read_parquet(CASES / "fertility_religiosity" / "data.parquet")
    assert detect_repeated_units(data, notes=case["column_notes"]) == []


def test_a_sessions_file_where_a_third_of_users_return_is_repeated() -> None:
    rng = np.random.default_rng(5)
    counts = np.where(rng.random(1500) < 0.31, 2, 1)
    users = np.repeat(np.arange(1500), counts)
    units = detect_repeated_units(frame(rows=len(users), user_id=users))
    assert [(u.name, u.n_units) for u in units] == [("user_id", 1500)]
    assert 1.2 < units[0].rows_per_unit < 2


def test_a_few_stray_repeats_are_not_a_repeated_unit() -> None:
    assert detect_repeated_units(frame(row_id=np.arange(600) % 550)) == []


def grunfeld() -> pd.DataFrame:
    firms = np.repeat(np.arange(11), 20)
    years = np.tile(np.arange(1935, 1955), 11)
    return pd.DataFrame({"inv": np.arange(220.0), "firm": firms, "year": years})


def test_a_small_panel_with_a_time_column_is_a_repeated_unit() -> None:
    units = detect_repeated_units(grunfeld(), exclude={"inv"})
    assert [(u.name, u.n_units, u.rows_per_unit) for u in units] == [("firm", 11, 20.0)]


def test_an_entity_column_without_a_time_column_is_not_a_panel() -> None:
    assert detect_repeated_units(grunfeld().drop(columns="year")) == []


def test_an_entity_that_does_not_make_a_panel_with_time_is_not_a_unit() -> None:
    assert detect_repeated_units(grunfeld().assign(firm=lambda d: d["firm"] % 3)) == []
    assert detect_repeated_units(grunfeld().assign(year=1)) == []


def test_treatment_and_group_columns_with_few_levels_are_not_units() -> None:
    rng = np.random.default_rng(1)
    data = frame(
        variant=rng.integers(0, 2, 600),
        group=rng.integers(0, 4, 600),
        arm=rng.integers(0, 3, 600),
        gender=rng.integers(0, 2, 600),
        department=rng.integers(0, 4, 600),
        year=rng.integers(2000, 2005, 600),
    )
    assert detect_repeated_units(data) == []


def test_exact_duplicate_rows_are_counted_and_profiled() -> None:
    data = pd.DataFrame({"a": [1, 1, 2, 2, 2, 3], "b": list("xxyyyz")})
    assert count_duplicate_rows(data) == 3
    assert profile_dataframe(data, "d").duplicate_rows == 3
