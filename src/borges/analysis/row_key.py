"""The column that names each row, so the rows two implementations fit can be compared.

The harness gives every step a fresh 0..n-1 index, so row positions mean nothing across steps;
a column with one distinct value per row and none missing still names the row at the model.
A column that holds personal data or free text never names the rows, because the keys are stored
in the run events; without a safe column there is no key and no row names are reported.
"""

from __future__ import annotations

import re

from borges.analysis.models import ColumnProfile, DatasetProfile
from borges.armor.profile_pii import column_values, unsafe_key_columns

SHORT_CODE_LENGTH = 20
NON_TEXT = ("int", "uint", "float", "bool", "datetime")
ID_NAME = re.compile(r"(?:^|_)id$|^id(?:_|$)|ID$|Id$", re.IGNORECASE)


def _is_integer(dtype: str) -> bool:
    return dtype.startswith(("int", "uint"))


def _short_code(profile: DatasetProfile, column: ColumnProfile) -> bool:
    values = column_values(profile, column)
    return bool(values) and all(len(v) <= SHORT_CODE_LENGTH and not v.split()[1:] for v in values)


def row_key(profile: DatasetProfile) -> str | None:
    unsafe = unsafe_key_columns(profile)
    unique = [
        c
        for c in profile.columns
        if c.n_missing == 0 and c.n_unique == profile.n_rows and c.name not in unsafe
    ]
    named = [c for c in unique if ID_NAME.search(c.name)]
    integers = [c for c in unique if _is_integer(c.dtype)]
    codes = [c for c in unique if not c.dtype.startswith(NON_TEXT) and _short_code(profile, c)]
    chosen = named or integers or codes
    return chosen[0].name if chosen else None
