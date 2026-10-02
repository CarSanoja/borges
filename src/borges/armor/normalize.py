from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from borges.armor.decoders import (
    decode_base64_tokens,
    decode_hex_tokens,
    decode_tag_characters,
    join_spaced_letters,
    rot13,
    unescape_markup,
)

TECHNIQUE_PLAIN = "plain"
TECHNIQUE_UNICODE = "unicode-folded"
TECHNIQUE_LEET = "leetspeak"
TECHNIQUE_REVERSED = "reversed"
TECHNIQUE_BASE64 = "base64"
TECHNIQUE_HEX = "hex"
TECHNIQUE_ROT13 = "rot13"
TECHNIQUE_SPACED = "spaced-letters"
TECHNIQUE_TAGS = "unicode-tags"
TECHNIQUE_ESCAPED = "escaped"
MAX_DEPTH = 3
MAX_VARIANTS = 40

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


def _layers(text: str) -> list[tuple[str, str]]:
    layers = [
        *((TECHNIQUE_BASE64, item) for item in decode_base64_tokens(text)),
        *((TECHNIQUE_HEX, item) for item in decode_hex_tokens(text)),
        (TECHNIQUE_ROT13, rot13(fold_homoglyphs(text))),
    ]
    for technique, decoded in (
        (TECHNIQUE_TAGS, decode_tag_characters(text)),
        (TECHNIQUE_ESCAPED, unescape_markup(text)),
    ):
        if decoded is not None:
            layers.append((technique, decoded))
    return layers


def variants_of(text: str) -> tuple[Variant, ...]:
    base = canonical(text)
    candidates = [
        Variant(base, TECHNIQUE_PLAIN),
        Variant(canonical(deleet(fold_homoglyphs(text))), TECHNIQUE_LEET),
        Variant(base[::-1], TECHNIQUE_REVERSED),
        Variant(canonical(join_spaced_letters(fold_homoglyphs(text))), TECHNIQUE_SPACED),
    ]
    seen: set[str] = set()
    unique: list[Variant] = []
    for variant in candidates:
        if variant.text not in seen:
            seen.add(variant.text)
            unique.append(variant)
    frontier = [(text, "")]
    for _ in range(MAX_DEPTH):
        following: list[tuple[str, str]] = []
        for source, trail in frontier:
            for technique, decoded in _layers(source):
                label = f"{trail}>{technique}" if trail else technique
                folded = canonical(decoded)
                if folded in seen or len(unique) >= MAX_VARIANTS:
                    continue
                seen.add(folded)
                unique.append(Variant(folded, label))
                following.append((decoded, label))
        frontier = following
    return tuple(unique)
