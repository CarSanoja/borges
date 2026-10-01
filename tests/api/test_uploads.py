from __future__ import annotations

import io

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
