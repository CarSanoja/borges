from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ("README.md", "ARCHITECTURE.md", "PRODUCT.md", "SECURITY.md")
PRIVATE = ("notes/", "research/", "runs/", "data/raw/")
CITED = re.compile(r"`([^`\s]+)`")


def _public_docs() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "evidence"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    return [ROOT / d for d in DOCS] + [ROOT / p for p in listed if p.endswith(".md")]


def test_public_docs_do_not_cite_files_kept_out_of_the_repository() -> None:
    """Naming where the app writes (`runs/<id>/...`) is fine; citing a file as evidence is not."""
    cited = [
        f"{doc.relative_to(ROOT)}: {path}"
        for doc in _public_docs()
        for path in CITED.findall(doc.read_text(encoding="utf-8"))
        if path.startswith(PRIVATE) and "<" not in path and path.rstrip("/") + "/" not in PRIVATE
    ]
    assert cited == []
