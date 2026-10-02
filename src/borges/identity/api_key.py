from __future__ import annotations

import hashlib
import hmac
import re
import secrets

KEY_PREFIX = "bk_"
NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
DURATION_PATTERN = re.compile(r"(\d+)([smhdw])")
UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def valid_name(name: str) -> bool:
    return NAME_PATTERN.fullmatch(name) is not None


def parse_duration(raw: str) -> float | None:
    text = raw.strip().lower()
    if text in ("", "never", "none"):
        return None
    match = DURATION_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError(f"cannot read duration '{raw}'; use forms like 30d, 12h, 90m or never")
    seconds = int(match.group(1)) * UNIT_SECONDS[match.group(2)]
    if seconds <= 0:
        raise ValueError("duration must be positive")
    return float(seconds)


def new_key_id() -> str:
    return secrets.token_hex(6)


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def new_salt() -> str:
    return secrets.token_hex(16)


def format_token(key_id: str, secret: str) -> str:
    return f"{KEY_PREFIX}{key_id}_{secret}"


def parse_token(token: str) -> tuple[str, str] | None:
    if not token.startswith(KEY_PREFIX):
        return None
    parts = token[len(KEY_PREFIX) :].split("_", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def hash_secret(salt: str, secret: str) -> str:
    return hmac.new(bytes.fromhex(salt), secret.encode("utf-8"), hashlib.sha256).hexdigest()


def secret_matches(salt: str, expected: str, secret: str) -> bool:
    return hmac.compare_digest(hash_secret(salt, secret), expected)
