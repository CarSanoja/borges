from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from borges.fleet.fingerprints import code_sha, prompt_sha, schema_sha


class One(BaseModel):
    a: int


class Two(BaseModel):
    a: int
    b: str = ""


def test_schema_sha_follows_the_schema() -> None:
    assert schema_sha(One) == schema_sha(One)
    assert schema_sha(One) != schema_sha(Two)
    assert schema_sha(None) is None


def test_prompt_sha_follows_the_text() -> None:
    assert prompt_sha("a") != prompt_sha("b")
    assert prompt_sha(None) is None


def test_code_sha_follows_file_content(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    before = code_sha(("a.py",), tmp_path)
    (tmp_path / "a.py").write_text("x = 2\n")
    assert code_sha(("a.py",), tmp_path) != before
    assert code_sha((), tmp_path) is None
