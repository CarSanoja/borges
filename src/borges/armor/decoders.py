from __future__ import annotations

import base64
import binascii
import codecs
import re

MIN_DECODED_CHARS = 8
MIN_TEXT_RATIO = 0.75
BASE64_TOKEN = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
HEX_TOKEN = re.compile(r"(?:[0-9a-fA-F]{2}){8,}")
SPACED_LETTERS = re.compile(r"(?<![^\W_])(?:[^\W_][\s.\-_*|/]){3,}[^\W_](?![^\W_])")
SEPARATOR_RUN = re.compile(r"[\s.\-_*|/]")


def looks_like_text(value: str) -> bool:
    if len(value) < MIN_DECODED_CHARS or not value.isprintable():
        return False
    readable = sum(1 for char in value if char.isalpha() or char.isspace())
    return readable >= MIN_TEXT_RATIO * len(value)


def decode_base64_tokens(text: str) -> list[str]:
    decoded: list[str] = []
    for match in BASE64_TOKEN.finditer(text):
        token = match.group(0).rstrip("=")
        padding = -len(token) % 4
        if padding == 3:
            continue
        try:
            raw = base64.b64decode(token + "=" * padding, validate=True).decode("utf-8")
        except (binascii.Error, ValueError, UnicodeDecodeError):
            continue
        if looks_like_text(raw):
            decoded.append(raw)
    return decoded


def decode_hex_tokens(text: str) -> list[str]:
    decoded: list[str] = []
    for match in HEX_TOKEN.finditer(text):
        try:
            raw = bytes.fromhex(match.group(0)).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        if looks_like_text(raw):
            decoded.append(raw)
    return decoded


def rot13(text: str) -> str:
    return codecs.encode(text, "rot13")


def join_spaced_letters(text: str) -> str:
    return SPACED_LETTERS.sub(lambda m: SEPARATOR_RUN.sub("", m.group(0)), text)
