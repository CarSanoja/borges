from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass

_DECODER = json.JSONDecoder()
_SAMPLE_KEY = re.compile(r'"sample_rows"\s*:\s*')
_ARRAY_OF_OBJECTS = re.compile(r"\[\s*\{")
_OBJECT_OF_LISTS = re.compile(r"\{\s*[\"']\w+[\"']\s*:\s*\[")
_PROFILE_MARKERS = ('"n_missing"', '"n_unique"')
MAX_REPR_TRIES = 40
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
    if not rows or not all(_scalar_record(r) for r in rows):
        return False
    first = rows[0]
    assert isinstance(first, dict)
    keys = set(first)
    return _grounded(keys, columns) and all(set(r) == keys for r in rows if isinstance(r, dict))


def _decoded_list(text: str, start: int) -> object:
    try:
        return _DECODER.raw_decode(text, start)[0]
    except ValueError:
        pass
    closers = [m.end() for m in re.finditer(r"\]", text[start:])][:MAX_REPR_TRIES]
    for end in closers:
        try:
            return ast.literal_eval(text[start : start + end])
        except (ValueError, SyntaxError, MemoryError, RecursionError):
            continue
    return None


def _is_column_dump(value: object, columns: frozenset[str]) -> int:
    if not isinstance(value, dict) or not _grounded(set(value), columns):
        return 0
    lengths = {len(v) for v in value.values() if isinstance(v, list)}
    return lengths.pop() if len(lengths) == 1 else 0


def record_dump_sizes(text: str, skip: list[SampleSpan], columns: frozenset[str]) -> list[int]:
    if not columns:
        return []
    sizes: list[int] = []
    for match in _ARRAY_OF_OBJECTS.finditer(text):
        if any(span.start <= match.start() < span.end for span in skip):
            continue
        value = _decoded_list(text, match.start())
        if isinstance(value, list) and _is_record_dump(value, columns):
            sizes.append(len(value))
    for match in _OBJECT_OF_LISTS.finditer(text):
        try:
            value, _ = _DECODER.raw_decode(text, match.start())
        except ValueError:
            continue
        size = _is_column_dump(value, columns)
        if size:
            sizes.append(size)
    sizes.append(jsonl_dump_size(text, columns))
    return sizes


def jsonl_dump_size(text: str, columns: frozenset[str]) -> int:
    best = run = 0
    for line in text.splitlines():
        stripped = line.strip().rstrip(",")
        record = None
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                record = json.loads(stripped)
            except ValueError:
                record = None
        if _scalar_record(record) and _grounded(set(record), columns):
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def _header_delimiter(line: str, columns: frozenset[str]) -> str | None:
    for delimiter in _DELIMITERS:
        fields = [f.strip().strip('"') for f in line.split(delimiter) if f.strip().strip('"')]
        others = [f for f in fields if f not in columns]
        if len(fields) >= MIN_DUMP_KEYS and len(others) <= 1 and _grounded(set(fields), columns):
            return delimiter
    return None


def _names_again(line: str, delimiter: str, columns: frozenset[str]) -> bool:
    fields = {f.strip().strip("'\"[]() ") for f in line.split(delimiter)}
    return len(fields & columns) >= min(MIN_DUMP_KEYS, len(columns))


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
        followers = lines[index + 1 :]
        while followers and not followers[0].strip():
            followers = followers[1:]
        for follower in followers:
            if follower.count(delimiter) != width or _names_again(follower, delimiter, columns):
                break
            rows += 1
        best = max(best, rows)
    return best


def has_profile(text: str) -> bool:
    return all(marker in text for marker in _PROFILE_MARKERS)
