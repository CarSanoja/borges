from __future__ import annotations

import io
import zipfile

import pandas as pd
import pytest

from borges.api.table_reader import read_table, sniff_delimiter

SPANISH = "\n".join(["id;ingresos;año"] + [f"{i};1.234,5;mañana" for i in range(60)])


def test_semicolon_decimal_comma_bom_file_is_read() -> None:
    content = b"\xef\xbb\xbf" + SPANISH.encode("utf-8")
    df = read_table(content, "export.csv")
    assert list(df.columns) == ["id", "ingresos", "año"]
    assert df["ingresos"].iloc[0] == 1234.5
    assert df["año"].iloc[0] == "mañana"
    assert len(df) == 60


def test_plain_comma_decimals_without_thousands() -> None:
    text = "a;b\n" + "\n".join(f"{i};{i},25" for i in range(5))
    df = read_table(text.encode(), "x.csv")
    assert df["b"].tolist() == [0.25, 1.25, 2.25, 3.25, 4.25]


def test_point_decimals_in_a_semicolon_file_survive() -> None:
    df = read_table(b"a;b\n1;2.5\n2;3.75\n", "x.csv")
    assert df["b"].tolist() == [2.5, 3.75]


def test_text_columns_are_not_turned_into_numbers() -> None:
    df = read_table(b"a;b\n1;1.2.3\n2;x\n", "x.csv")
    assert df["b"].tolist() == ["1.2.3", "x"]


def test_latin1_fallback() -> None:
    df = read_table("id;año\n1;ñu\n2;ñandú\n".encode("latin-1"), "x.csv")
    assert list(df.columns) == ["id", "año"]
    assert df["año"].tolist() == ["ñu", "ñandú"]


def test_tab_delimited_file() -> None:
    df = read_table(b"a\tb\tc\n1\t2.5\tx\n3\t4.5\ty\n", "x.tsv")
    assert list(df.columns) == ["a", "b", "c"]
    assert df["b"].tolist() == [2.5, 4.5]


def test_pipe_delimited_file() -> None:
    df = read_table(b"a|b\n1|2\n3|4\n", "x.csv")
    assert list(df.columns) == ["a", "b"]


@pytest.mark.parametrize(
    ("text", "delimiter"),
    [("a,b\n1,2\n", ","), ("a;b;c\n1;2;3\n", ";"), ("a\tb\n1\t2\n", "\t"), ("a|b\n1|2\n", "|")],
)
def test_sniff_delimiter(text: str, delimiter: str) -> None:
    assert sniff_delimiter(text) == delimiter


def test_commas_inside_quotes_do_not_win_over_the_real_delimiter() -> None:
    text = 'name;note\n"a, b, c";1\n"d, e, f";2\n'
    assert sniff_delimiter(text) == ";"


def xlsx_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xl/workbook.xml", "<workbook/>")
    return buffer.getvalue()


@pytest.mark.parametrize(
    "content", [xlsx_bytes(), b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\xa4" * 20]
)
def test_excel_workbook_renamed_csv_gets_a_plain_message(content: bytes) -> None:
    with pytest.raises(ValueError, match="CSV UTF-8") as raised:
        read_table(content, "renamed.csv")
    assert "codec" not in str(raised.value)
    assert "Excel" in str(raised.value)


def test_parquet_is_still_read() -> None:
    buffer = io.BytesIO()
    pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_parquet(buffer)
    assert len(read_table(buffer.getvalue(), "x.parquet")) == 2
