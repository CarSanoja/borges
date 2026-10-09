from __future__ import annotations

import io
import json
import re

import pandas as pd
import pytest

from borges.analysis.models import DatasetProfile
from borges.api import uploads as uploads_module
from borges.api.uploads import UploadStore


@pytest.fixture(autouse=True)
def fake_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    def profile(df: pd.DataFrame, name: str, sample: int = 5) -> DatasetProfile:
        return DatasetProfile(name=name, n_rows=len(df), columns=[])

    monkeypatch.setattr(uploads_module.profile_module, "profile_dataframe", profile)


def csv_bytes(rows: int = 60, cols: int = 3) -> bytes:
    df = pd.DataFrame({f"c{i}": range(rows) for i in range(cols)})
    return df.to_csv(index=False).encode()


def test_put_and_get_roundtrip(tmp_path) -> None:
    store = UploadStore(tmp_path / "up")
    upload_id, profile = store.put(csv_bytes(), "data.csv")
    assert profile.n_rows == 60
    data, name = store.get(upload_id)
    assert name == "data.csv"
    assert len(pd.read_parquet(io.BytesIO(data))) == 60


def test_filename_is_reduced_to_basename(tmp_path) -> None:
    store = UploadStore(tmp_path)
    upload_id, _ = store.put(csv_bytes(), "../../evil.csv")
    assert store.get(upload_id)[1] == "evil.csv"


@pytest.mark.parametrize(
    "payload",
    [b"", b"a,b\n1,2\n", csv_bytes(rows=10), csv_bytes(cols=1), b"\x00\xff\xfe"],
)
def test_invalid_csv_rejected(tmp_path, payload: bytes) -> None:
    with pytest.raises(ValueError):
        UploadStore(tmp_path).put(payload, "x.csv")


def test_too_large_rejected(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uploads_module, "MAX_BYTES", 10)
    with pytest.raises(ValueError, match="20 MB"):
        UploadStore(tmp_path).put(csv_bytes(), "x.csv")


@pytest.mark.parametrize("upload_id", ["../x", "nope", "0" * 32])
def test_get_unknown_raises(tmp_path, upload_id: str) -> None:
    with pytest.raises(KeyError):
        UploadStore(tmp_path).get(upload_id)


def test_quota_rejects_and_removes_the_overflowing_upload(tmp_path) -> None:
    from borges.api.uploads import UploadQuotaError

    store = UploadStore(tmp_path, quota_mb=0)
    with pytest.raises(UploadQuotaError):
        store.put(csv_bytes(), "d.csv")
    assert list(tmp_path.glob("*.parquet")) == []


def test_quota_allows_uploads_under_the_limit(tmp_path) -> None:
    store = UploadStore(tmp_path, quota_mb=50)
    store.put(csv_bytes(), "a.csv")
    store.put(csv_bytes(), "b.csv")
    assert len(list(tmp_path.glob("*.parquet"))) == 2


def parquet_bytes(rows: int = 60) -> bytes:
    buffer = io.BytesIO()
    pd.DataFrame({"a": range(rows), "b": range(rows)}).to_parquet(buffer)
    return buffer.getvalue()


def test_parquet_upload_is_accepted(tmp_path) -> None:
    store = UploadStore(tmp_path)
    upload_id, profile = store.put(parquet_bytes(), "data.parquet")
    assert profile.n_rows == 60
    data, name = store.get(upload_id)
    assert name == "data.parquet"
    assert len(pd.read_parquet(io.BytesIO(data))) == 60


def test_parquet_is_detected_by_content_when_the_name_lies(tmp_path) -> None:
    upload_id, _ = UploadStore(tmp_path).put(parquet_bytes(), "data.csv")
    assert upload_id


def test_corrupt_parquet_is_rejected_with_a_clear_message(tmp_path) -> None:
    with pytest.raises(ValueError, match="parquet file"):
        UploadStore(tmp_path).put(b"PAR1 not really", "x.parquet")


def stored_columns(store: UploadStore, upload_id: str) -> list[str]:
    return list(pd.read_parquet(io.BytesIO(store.get(upload_id)[0])).columns)


def test_hostile_column_name_is_stored_as_identifier(tmp_path) -> None:
    hostile = "I(__import__('os').system('x'))"
    df = pd.DataFrame({hostile: range(60), "y": range(60)})
    store = UploadStore(tmp_path)
    upload_id, _ = store.put(df.to_csv(index=False).encode(), "d.csv")
    columns = stored_columns(store, upload_id)
    assert all(re.fullmatch(r"[a-z_][a-z0-9_]*", c) for c in columns)
    assert "(" not in "".join(columns) and "__" not in "".join(columns)
    meta = json.loads((tmp_path / f"{upload_id}.json").read_text())
    assert meta["columns"][columns[0]] == hostile


def test_column_names_are_normalised_and_deduplicated(tmp_path) -> None:
    df = pd.DataFrame(
        {"Age (Years)": range(60), "age_years_": range(60), "": range(60), "9lives": range(60)}
    )
    df.columns = ["Age (Years)", "age_years_", "", "9lives"]
    store = UploadStore(tmp_path)
    upload_id, _ = store.put(df.to_csv(index=False).encode(), "d.csv")
    assert stored_columns(store, upload_id) == [
        "age_years",
        "age_years_2",
        "unnamed_2",
        "_9lives",
    ]


def test_forbidden_names_are_not_kept_as_columns(tmp_path) -> None:
    df = pd.DataFrame({"os": range(60), "open": range(60)})
    store = UploadStore(tmp_path)
    upload_id, _ = store.put(df.to_csv(index=False).encode(), "d.csv")
    assert stored_columns(store, upload_id) == ["os_col", "open_col"]


def test_empty_column_name_is_replaced() -> None:
    frame = pd.DataFrame([[1, 2]], columns=["", "!!!"])
    normalised, mapping = uploads_module.normalise_columns(frame)
    assert list(normalised.columns) == ["column", "column_2"]
    assert mapping == {"column": "", "column_2": "!!!"}


def test_semicolon_decimal_comma_bom_upload_is_accepted(tmp_path) -> None:
    lines = ["id;ingresos;año"] + [f"{i};{i},5;mañana" for i in range(60)]
    content = b"\xef\xbb\xbf" + "\n".join(lines).encode()
    store = UploadStore(tmp_path)
    upload_id, profile = store.put(content, "export.csv")
    assert profile.n_rows == 60
    frame = pd.read_parquet(io.BytesIO(store.get(upload_id)[0]))
    assert list(frame.columns) == ["id", "ingresos", "anio"]
    assert frame["ingresos"].iloc[1] == 1.5


def test_tab_delimited_upload_is_accepted(tmp_path) -> None:
    lines = ["a\tb\tc"] + [f"{i}\t{i}.5\tx" for i in range(60)]
    _, profile = UploadStore(tmp_path).put("\n".join(lines).encode(), "export.tsv")
    assert profile.n_rows == 60


def test_xlsx_renamed_csv_is_explained(tmp_path) -> None:
    with pytest.raises(ValueError, match="CSV UTF-8"):
        UploadStore(tmp_path).put(b"PK\x03\x04" + b"\xa4" * 50, "book.csv")


def test_all_empty_columns_are_dropped_and_reported(tmp_path) -> None:
    df = pd.DataFrame({"a": range(60), "b": range(60), "vacia": [None] * 60, "tail": [None] * 60})
    store = UploadStore(tmp_path)
    upload_id, profile = store.put(df.to_csv(index=False).encode(), "d.csv")
    frame = pd.read_parquet(io.BytesIO(store.get(upload_id)[0]))
    assert list(frame.columns) == ["a", "b"]
    dropped = store.dropped_columns(upload_id)
    assert [d["column"] for d in dropped] == ["vacia", "tail"]
    assert all(d["reason"] for d in dropped)
    assert profile.n_rows == 60


def test_no_empty_columns_reports_nothing(tmp_path) -> None:
    store = UploadStore(tmp_path)
    upload_id, _ = store.put(csv_bytes(), "d.csv")
    assert store.dropped_columns(upload_id) == []


def test_too_few_columns_after_dropping_is_explained(tmp_path) -> None:
    df = pd.DataFrame({"a": range(60), "vacia": [None] * 60})
    with pytest.raises(ValueError, match="1 empty columns were dropped"):
        UploadStore(tmp_path).put(df.to_csv(index=False).encode(), "d.csv")


def test_too_few_rows_says_why_and_how_many(tmp_path) -> None:
    with pytest.raises(ValueError, match="has 10 rows") as raised:
        UploadStore(tmp_path).put(csv_bytes(rows=10), "d.csv")
    assert "too few degrees of freedom" in str(raised.value)
    assert "at least 20" in str(raised.value)


def test_one_class_measured_before_and_after_is_accepted(tmp_path) -> None:
    _, profile = UploadStore(tmp_path).put(csv_bytes(rows=48), "d.csv")
    assert profile.n_rows == 48
