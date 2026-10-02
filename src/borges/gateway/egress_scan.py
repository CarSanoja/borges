from __future__ import annotations

import json
import re
from dataclasses import dataclass

_DECODER = json.JSONDecoder()
_SAMPLE_KEY = re.compile(r'"sample_rows"\s*:\s*')
_ARRAY_OF_OBJECTS = re.compile(r"\[\s*\{")
_PROFILE_MARKERS = ('"n_missing"', '"n_unique"')
MIN_DUMP_ROWS = 6
MIN_DUMP_KEYS = 3
_DELIMITERS = (",", "\t", "|", ";")


@dataclass(frozen=True)
class SampleSpan:
    start: int
    end: int
    rows: list[object]


def find_sample_rows(text: str) -> list[SampleSpan]:
    spans: list[SampleSpan] = []
    for match in _SAMPLE_KEY.finditer(text):
        try:
            value, end = _DECODER.raw_decode(text, match.end())
        except ValueError:
            continue
        if isinstance(value, list):
            spans.append(SampleSpan(match.end(), end, value))
    return spans


def _scalar_record(item: object) -> bool:
    return isinstance(item, dict) and all(
        value is None or isinstance(value, str | int | float | bool) for value in item.values()
    )


def _grounded(keys: set[str], columns: frozenset[str]) -> bool:
    return len(keys & columns) >= min(MIN_DUMP_KEYS, len(columns))


def _is_record_dump(rows: list[object], columns: frozenset[str]) -> bool:
    if len(rows) < MIN_DUMP_ROWS or not all(_scalar_record(r) for r in rows):
        return False
    first = rows[0]
    assert isinstance(first, dict)
    keys = set(first)
    return _grounded(keys, columns) and all(set(r) == keys for r in rows if isinstance(r, dict))


def record_dump_sizes(text: str, skip: list[SampleSpan], columns: frozenset[str]) -> list[int]:
    if not columns:
        return []
    sizes: list[int] = []
    for match in _ARRAY_OF_OBJECTS.finditer(text):
        if any(span.start <= match.start() < span.end for span in skip):
            continue
        try:
            value, _ = _DECODER.raw_decode(text, match.start())
        except ValueError:
            continue
        if isinstance(value, list) and _is_record_dump(value, columns):
            sizes.append(len(value))
    return sizes


def _header_delimiter(line: str, columns: frozenset[str]) -> str | None:
    for delimiter in _DELIMITERS:
        fields = {field.strip().strip('"') for field in line.split(delimiter)}
        if len(fields) >= MIN_DUMP_KEYS and _grounded(fields, columns):
            return delimiter
    return None


def delimited_dump_size(text: str, columns: frozenset[str]) -> int:
    if not columns:
        return 0
    lines = text.splitlines()
    best = 0
    for index, line in enumerate(lines):
        delimiter = _header_delimiter(line, columns)
        if delimiter is None:
            continue
        width = line.count(delimiter)
        rows = 0
        for follower in lines[index + 1 :]:
            if follower.count(delimiter) != width:
                break
            rows += 1
        best = max(best, rows)
    return best


def has_profile(text: str) -> bool:
    return all(marker in text for marker in _PROFILE_MARKERS)
