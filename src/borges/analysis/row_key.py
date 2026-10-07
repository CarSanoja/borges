"""The column that names each row, so the rows two implementations fit can be compared.

The harness gives every step a fresh 0..n-1 index, so row positions mean nothing across steps;
a column with one distinct value per row and none missing still names the row at the model.
"""

from __future__ import annotations

import re

from borges.analysis.models import DatasetProfile

ID_NAME = re.compile(r"(?:^|_)id$|^id(?:_|$)|ID$|Id$", re.IGNORECASE)


def row_key(profile: DatasetProfile) -> str | None:
    unique = [c for c in profile.columns if c.n_missing == 0 and c.n_unique == profile.n_rows]
    named = [c for c in unique if ID_NAME.search(c.name)]
    plain = [c for c in unique if not c.dtype.startswith(("float", "datetime"))]
    chosen = named or plain
    return chosen[0].name if chosen else None
