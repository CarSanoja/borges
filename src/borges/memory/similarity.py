from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass

DIMENSIONS = 512
TOKEN = re.compile(r"[a-z0-9_]+")


def _tokens(text: str) -> list[str]:
    words = TOKEN.findall(text.lower())
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:], strict=False)]


def embed(text: str) -> list[float]:
    """Hashing embedder: signed bag of words and bigrams in a fixed-size, L2-normalised vector."""
    vector = [0.0] * DIMENSIONS
    for token in _tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        slot = int.from_bytes(digest[:4], "big") % DIMENSIONS
        vector[slot] += 1.0 if digest[4] & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


@dataclass(frozen=True)
class Scored:
    index: int
    score: float


def best_match(query: str, candidates: Iterable[str], threshold: float) -> Scored | None:
    target = embed(query)
    best: Scored | None = None
    for index, text in enumerate(candidates):
        score = cosine(target, embed(text))
        if score >= threshold and (best is None or score > best.score):
            best = Scored(index, score)
    return best
