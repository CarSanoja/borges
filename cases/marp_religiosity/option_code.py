from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "marp_shared"))

from marp_options import option_codes  # noqa: E402

OPTIONS: dict[str, str] = option_codes(1)
