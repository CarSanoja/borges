from __future__ import annotations

import csv
import io
import re

import pandas as pd

PARQUET_MAGIC = b"PAR1"
ZIP_MAGIC = b"PK\x03\x04"
OLE_MAGIC = b"\xd0\xcf\x11\xe0"
DELIMITERS = (",", ";", "\t", "|")
SNIFF_LINES = 8
EXCEL_MESSAGE = (
    'This is an Excel workbook, not a CSV. In Excel choose File > Save As > "CSV UTF-8" '
    "and upload that file."
)
_EUROPEAN = re.compile(r"^[+-]?(\d{1,3}(\.\d{3})+|\d+)(,\d+)?$")
_POINT_DECIMAL = re.compile(r"^[+-]?\d+\.\d+$")


def is_parquet(content: bytes, filename: str) -> bool:
    return content[:4] == PARQUET_MAGIC or filename.lower().endswith(".parquet")


def is_excel(content: bytes) -> bool:
    return content[:4] in (ZIP_MAGIC, OLE_MAGIC)


def decode_text(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def sniff_delimiter(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()][:SNIFF_LINES]
    best, best_score = ",", (False, 0)
    for delimiter in DELIMITERS:
        counts = [len(row) - 1 for row in csv.reader(lines, delimiter=delimiter)]
        if not counts or counts[0] == 0:
            continue
        score = (len(set(counts)) == 1, counts[0])
        if score > best_score:
            best, best_score = delimiter, score
    return best


def _convert_column(values: pd.Series) -> pd.Series:
    present = values.dropna().astype(str).str.strip()
    if present.empty:
        return values
    if present.map(lambda v: bool(_EUROPEAN.match(v))).all():
        cleaned = values.astype(str).str.strip().str.replace(".", "", regex=False)
        cleaned = cleaned.str.replace(",", ".", regex=False)
        return pd.to_numeric(cleaned.where(values.notna()))
    if present.map(lambda v: bool(_POINT_DECIMAL.match(v))).all():
        return pd.to_numeric(values.astype(str).str.strip().where(values.notna()))
    return values


def _read_delimited(text: str) -> pd.DataFrame:
    delimiter = sniff_delimiter(text)
    european = delimiter == ";"
    df = pd.read_csv(
        io.StringIO(text),
        sep=delimiter,
        decimal="," if european else ".",
        engine="python" if delimiter == "|" else "c",
    )
    if not european:
        return df
    for column in df.columns:
        if not pd.api.types.is_numeric_dtype(df[column]) and not pd.api.types.is_bool_dtype(
            df[column]
        ):
            df[column] = _convert_column(df[column])
    return df


def read_table(content: bytes, filename: str) -> pd.DataFrame:
    parquet = is_parquet(content, filename)
    if not parquet and is_excel(content):
        raise ValueError(EXCEL_MESSAGE)
    try:
        if parquet:
            return pd.read_parquet(io.BytesIO(content))
        return _read_delimited(decode_text(content))
    except Exception as exc:
        kind = "parquet file" if parquet else "CSV"
        raise ValueError(f"The file is not a readable {kind}: {exc}") from exc
