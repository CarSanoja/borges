from __future__ import annotations

from borges.analysis.models import ColumnProfile, DatasetProfile
from borges.armor.profile_guard import guard_profile
from borges.armor.profile_pii import person_name_columns, unsafe_key_columns

NAMES = ["Maria Lopez", "John Smith", "Ana Ruiz", "Li Wei", "Omar Haddad"]


def hr_profile() -> DatasetProfile:
    return DatasetProfile(
        name="hr.csv",
        n_rows=1500,
        columns=[
            ColumnProfile(
                name="employee",
                dtype="object",
                n_missing=0,
                n_unique=1500,
                summary={"top_1": "Maria Lopez: 1", "top_2": "John Smith: 1"},
            ),
            ColumnProfile(
                name="department",
                dtype="object",
                n_missing=0,
                n_unique=6,
                summary={"top_1": "Sales: 400"},
            ),
            ColumnProfile(name="salary", dtype="int64", n_missing=0, n_unique=900),
            ColumnProfile(
                name="ssn",
                dtype="object",
                n_missing=0,
                n_unique=1500,
                summary={"top_1": "123-45-0000: 1"},
            ),
        ],
        sample_rows=[
            {"employee": n, "department": "Sales", "salary": 5000, "ssn": "123-45-0000"}
            for n in NAMES
        ],
    )


def test_name_column_is_found_by_values_and_department_is_not() -> None:
    assert person_name_columns(hr_profile()) == {"employee"}


def test_name_header_alone_marks_the_column() -> None:
    profile = hr_profile()
    profile.columns[1] = profile.columns[1].model_copy(update={"name": "Apellidos"})
    assert "Apellidos" in person_name_columns(profile)


def test_names_and_invalid_serial_ssn_are_redacted_everywhere() -> None:
    guarded, report = guard_profile(hr_profile())
    assert guarded.columns[0].summary["top_1"] == "[redacted:person_name]: 1"
    assert guarded.columns[1].summary["top_1"] == "Sales: 400"
    assert guarded.columns[3].summary["top_1"] == "[redacted:ssn]: 1"
    assert {row["employee"] for row in guarded.sample_rows} == {"[redacted:person_name]"}
    assert all(row["ssn"] == "[redacted:ssn]" for row in guarded.sample_rows)
    assert report.pii_counts()["person_name"] >= 5 and report.pii_counts()["ssn"] >= 5
    assert "Maria" not in guarded.model_dump_json()


def test_unsafe_key_columns_cover_names_and_pii() -> None:
    assert unsafe_key_columns(hr_profile()) == {"employee", "ssn"}
