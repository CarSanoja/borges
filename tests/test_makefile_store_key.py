from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_serve_paths_generate_the_store_key() -> None:
    assert "BORGES_STORE_KEY_AUTOGEN=true" in (ROOT / "Makefile").read_text()
    assert "BORGES_STORE_KEY_AUTOGEN=true" in (ROOT / "Dockerfile").read_text()
