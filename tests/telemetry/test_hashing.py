from __future__ import annotations

from borges.telemetry.hashing import canonical_json, sha256_json, sha256_text


def test_canonical_json_is_key_order_independent() -> None:
    assert canonical_json({"b": 1, "a": [1, 2]}) == canonical_json({"a": [1, 2], "b": 1})
    assert sha256_json({"b": 1, "a": 2}) == sha256_json({"a": 2, "b": 1})


def test_sha256_text_is_hex_digest() -> None:
    assert sha256_text("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
