from __future__ import annotations

import hashlib
import json


def universe_id(choices: dict[str, str]) -> str:
    canonical = json.dumps(sorted(choices.items()), separators=(",", ":"))
    return "u_" + hashlib.sha1(canonical.encode()).hexdigest()[:10]
