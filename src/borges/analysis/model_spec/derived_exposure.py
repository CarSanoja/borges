"""A 0/1 exposure the option derives from a text column, such as treatment = (variant == 'B').

The template codes that indicator itself from the text column and its level, so a spec naming the
derived indicator, a column that does not exist when the step runs, is rewritten to that pair.

A live fertility_religiosity run on 7 Oct 2026 named fertility_indicator (1 if
fertility_status=='high' else 0) and relationship_indicator (1 if relationship_group=='committed'
else 0) as exposure and moderator. Both text columns were built by earlier steps, so they are not
in the dataset profile, and the spec states two comparisons, so neither was rewritten; the
template was skipped and the free code reported the wrong coefficient. The comparison is read
from each name's own definition, and a column built earlier is taken at its stated level: the
template checks at run time that the level is a value of the column.
"""

from __future__ import annotations

import re

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.model_spec.validate_exposure import column_levels, is_text, profile_of
from borges.analysis.models import DatasetProfile

EQUALS = re.compile(r"""[`'"]?([A-Za-z_]\w*)[`'"]?\]?\s*==\s*['"]([^'"]+)['"]""")
CLAUSE_END = re.compile(r"[;,]|\.\s")
CLAUSE_CHARS = 120
AMBIGUOUS = ("", "")


def _text_levels(profile: DatasetProfile | None, available: list[str]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for name in available:
        column = profile_of(profile, name)
        if column is not None and is_text(column):
            found[name] = column_levels(column)
    return found


def _pairs(spec: ModelSpecOutput, text: str, levels: dict[str, list[str]]) -> set[tuple[str, str]]:
    stated = {(c, v) for c, v in EQUALS.findall(text) if v in levels.get(c, [])}
    if stated:
        return stated
    wanted = [v for v in (spec.exposure_level, spec.exposure) if v]
    return {(c, v) for c, values in levels.items() for v in wanted if v in values}


def _usable(column: str, level: str, available: list[str], profile: DatasetProfile | None) -> bool:
    if column not in available:
        return False
    known = profile_of(profile, column)
    if known is None:
        return True
    return is_text(known) and level in column_levels(known)


def _defined(
    name: str, text: str, available: list[str], profile: DatasetProfile | None
) -> tuple[str, str] | None:
    pairs: set[tuple[str, str]] = set()
    for match in re.finditer(rf"\b{re.escape(name)}\b", text):
        clause = text[match.end() : match.end() + CLAUSE_CHARS]
        end = CLAUSE_END.search(clause)
        found = EQUALS.findall(clause[: end.start()] if end else clause)
        if len(found) > 1:
            return AMBIGUOUS
        pairs.update(found)
    if not pairs:
        return None
    pair = next(iter(pairs))
    return pair if len(pairs) == 1 and _usable(*pair, available, profile) else AMBIGUOUS


def _moderator(
    spec: ModelSpecOutput, text: str, available: list[str], profile: DatasetProfile | None
) -> ModelSpecOutput:
    if spec.moderator is None or spec.moderator in available:
        return spec
    pair = _defined(spec.moderator, text, available, profile)
    if pair is None or pair == AMBIGUOUS:
        return spec
    standardize = [n for n in spec.standardize if n != spec.moderator]
    return spec.model_copy(
        update={"moderator": pair[0], "moderator_level": pair[1], "standardize": standardize}
    )


def derived_exposure(
    spec: ModelSpecOutput, text: str, available: list[str], profile: DatasetProfile | None
) -> ModelSpecOutput:
    if not spec.supported:
        return spec
    spec = _moderator(spec, text, available, profile)
    if spec.exposure is None or spec.exposure in available:
        return spec
    bound = _defined(spec.exposure, text, available, profile)
    if bound == AMBIGUOUS:
        return spec
    pairs = {bound} if bound else _pairs(spec, text, _text_levels(profile, available))
    if len(pairs) != 1:
        return spec
    column, level = next(iter(pairs))
    standardize = [n for n in spec.standardize if n != spec.exposure]
    return spec.model_copy(
        update={"exposure": column, "exposure_level": level, "standardize": standardize}
    )
