from __future__ import annotations

from pathlib import Path

from borges.llm.cache import DiskCache, cache_key

RECORD = {"model": "m", "text": "t", "parsed": {"a": 1}, "tokens_in": 1, "tokens_out": 2}


def test_key_is_stable_and_sensitive() -> None:
    base = cache_key("m", [{"role": "user", "content": "hi"}], "S", 10, 0.2)
    assert base == cache_key("m", [{"role": "user", "content": "hi"}], "S", 10, 0.2)
    assert base != cache_key("m2", [{"role": "user", "content": "hi"}], "S", 10, 0.2)
    assert base != cache_key("m", [{"role": "user", "content": "hi"}], None, 10, 0.2)
    assert base != cache_key("m", [{"role": "user", "content": "hi"}], "S", 11, 0.2)
    assert base != cache_key("m", [{"role": "user", "content": "hi"}], "S", 10, 0.3)


def test_put_get_roundtrip(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path / "nested")
    assert cache.get("k") is None
    cache.put("k", RECORD)
    assert cache.get("k") == RECORD
    assert [p.name for p in (tmp_path / "nested").iterdir()] == ["k.json"]


def test_corrupt_entry_is_a_miss(tmp_path: Path) -> None:
    (tmp_path / "k.json").write_text("{broken")
    assert DiskCache(tmp_path).get("k") is None
