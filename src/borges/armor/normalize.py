from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from borges.armor.decoders import (
    decode_base64_tokens,
    decode_hex_tokens,
    join_spaced_letters,
    rot13,
)

TECHNIQUE_PLAIN = "plain"
TECHNIQUE_UNICODE = "unicode-folded"
TECHNIQUE_LEET = "leetspeak"
TECHNIQUE_REVERSED = "reversed"
TECHNIQUE_BASE64 = "base64"
TECHNIQUE_HEX = "hex"
TECHNIQUE_ROT13 = "rot13"
TECHNIQUE_SPACED = "spaced-letters"

KEEP_CONTROLS = frozenset("\n\t\r ")
STRIPPED_CATEGORIES = frozenset({"Cc", "Cf", "Co", "Cs", "Mn", "Me"})

HOMOGLYPHS = {
    "а": "a",
    "в": "b",
    "е": "e",
    "к": "k",
    "м": "m",
    "н": "h",
    "о": "o",
    "р": "p",
    "с": "c",
    "т": "t",
    "у": "y",
    "х": "x",
    "ѕ": "s",
    "і": "i",
    "ј": "j",
    "һ": "h",
    "ԁ": "d",
    "ԛ": "q",
    "ԝ": "w",
    "ё": "e",
    "ї": "i",
    "ӏ": "l",
    "ɡ": "g",
    "ɑ": "a",
    "α": "a",
    "β": "b",
    "γ": "y",
    "ε": "e",
    "ι": "i",
    "κ": "k",
    "ν": "v",
    "ο": "o",
    "ρ": "p",
    "τ": "t",
    "υ": "u",
    "χ": "x",
    "ϲ": "c",
    "ո": "n",
    "օ": "o",
    "ս": "u",
    "ℓ": "l",
    "ı": "i",
    "ȷ": "j",
    "ƅ": "b",
    "ᴀ": "a",
    "ʙ": "b",
    "ᴄ": "c",
    "ᴅ": "d",
    "ᴇ": "e",
    "ɢ": "g",
    "ʜ": "h",
    "ɪ": "i",
    "ᴊ": "j",
    "ᴋ": "k",
    "ʟ": "l",
    "ᴍ": "m",
    "ɴ": "n",
    "ᴏ": "o",
    "ᴘ": "p",
    "ʀ": "r",
    "ᴛ": "t",
    "ᴜ": "u",
    "ᴠ": "v",
    "ᴡ": "w",
    "ʏ": "y",
    "ᴢ": "z",
}
LEET = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i"}

_UPPER = {key.upper(): value for key, value in HOMOGLYPHS.items() if not key.upper().isascii()}
_HOMOGLYPH_TABLE = str.maketrans({**HOMOGLYPHS, **_UPPER})
_LEET_TABLE = str.maketrans(LEET)
_SEPARATORS = re.compile(r"[\W_]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


@dataclass(frozen=True)
class Variant:
    text: str
    technique: str


def strip_invisible(text: str) -> str:
    kept = [
        char
        for char in text
        if char in KEEP_CONTROLS or unicodedata.category(char) not in STRIPPED_CATEGORIES
    ]
    return "".join(kept)


def fold_unicode(text: str) -> str:
    composed = unicodedata.normalize("NFKC", text)
    stripped = strip_invisible(composed)
    return unicodedata.normalize("NFKC", stripped)


def fold_homoglyphs(text: str) -> str:
    return fold_unicode(text).translate(_HOMOGLYPH_TABLE)


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC", "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    )


def canonical(text: str) -> str:
    return strip_accents(fold_homoglyphs(text)).lower()


def has_confusables(text: str) -> bool:
    return any(
        char in HOMOGLYPHS or unicodedata.category(char) in STRIPPED_CATEGORIES
        for char in text
        if char not in KEEP_CONTROLS
    )


def deleet(text: str) -> str:
    return text.translate(_LEET_TABLE)


def normalize_identifier(value: str) -> str:
    folded = _CAMEL.sub(" ", fold_homoglyphs(value))
    return _SEPARATORS.sub(" ", folded).strip().lower()


def variants_of(text: str) -> tuple[Variant, ...]:
    base = canonical(text)
    candidates = [
        Variant(base, TECHNIQUE_PLAIN),
        Variant(canonical(deleet(fold_homoglyphs(text))), TECHNIQUE_LEET),
        Variant(base[::-1], TECHNIQUE_REVERSED),
        Variant(canonical(join_spaced_letters(fold_homoglyphs(text))), TECHNIQUE_SPACED),
        Variant(canonical(rot13(fold_homoglyphs(text))), TECHNIQUE_ROT13),
    ]
    decoded = [
        *(Variant(canonical(item), TECHNIQUE_BASE64) for item in decode_base64_tokens(text)),
        *(Variant(canonical(item), TECHNIQUE_HEX) for item in decode_hex_tokens(text)),
    ]
    seen: set[str] = set()
    unique: list[Variant] = []
    for variant in [*candidates, *decoded]:
        if variant.text in seen:
            continue
        seen.add(variant.text)
        unique.append(variant)
    return tuple(unique)
