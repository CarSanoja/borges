from __future__ import annotations

import pandas as pd

from borges.armor.upload_scan import SCAN_VALUES_PER_COLUMN, scan_column, scan_dataframe


def test_columns_with_personal_data_are_reported_with_counts_only() -> None:
    frame = pd.DataFrame(
        {
            "id": range(10),
            "mail": ["a@b.co"] * 10,
            "free": ["ok"] * 9 + ["ssn 123-45-6789"],
            "dob": ["1985-03-02"] * 10,
            "order_date": ["2024-01-02"] * 10,
        }
    )
    summary = scan_dataframe(frame)
    kinds = {c.column: c.kinds for c in summary.columns}
    assert kinds == {
        "mail": {"email": 10},
        "free": {"ssn": 1},
        "dob": {"date_of_birth": 10},
    }
    assert summary.total_detections == 21
    assert "a@b.co" not in summary.model_dump_json()


def test_long_integer_card_numbers_are_found_but_ordinary_numbers_are_not() -> None:
    frame = pd.DataFrame({"card": [4111111111111111] * 3, "n": [1, 2, 3], "f": [0.5] * 3})
    assert [c.column for c in scan_dataframe(frame).columns] == ["card"]


def test_large_columns_are_sampled() -> None:
    series = pd.Series(["a@b.co"] * (SCAN_VALUES_PER_COLUMN * 3))
    found = scan_column(series, "mail")
    assert found is not None and found.scanned == SCAN_VALUES_PER_COLUMN
    assert found.total_rows == SCAN_VALUES_PER_COLUMN * 3


def test_clean_and_empty_columns_report_nothing() -> None:
    assert scan_column(pd.Series(["x", "y"]), "c") is None
    assert scan_column(pd.Series([None, None], dtype=object), "c") is None
    assert scan_column(pd.Series([True, False]), "b") is None
