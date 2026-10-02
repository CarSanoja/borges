from __future__ import annotations

import sys
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CASE_DIR.parent / "marp_shared"))

from marp_data import write_dataset  # noqa: E402

if __name__ == "__main__":
    write_dataset([CASE_DIR, CASE_DIR.parent / "marp_norms"])
