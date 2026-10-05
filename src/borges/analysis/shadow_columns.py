"""A changed copy of a dataset column written under a new name, such as campaign_w.

The steps after an option read the column's own name in every universe, so an option of a step
that does not produce the copy has no effect: a bank plan winsorised five columns into balance_w
and the like, an adversary capped campaign into campaign_capped, and both options gave the
baseline's result in every universe (b4e2f4e).
"""

from __future__ import annotations

import re

QUOTED = re.compile(r"""["']([A-Za-z_]\w*)["']""")
COPY_SUFFIX = re.compile(
    r"_(?:w|wins|winsori[sz]ed|cap|capped|clip|clipped|trim|trimmed|clean|cleaned|adj|"
    r"adjusted|new|mod|modified|transformed|t|log|ln|sqrt|z|std|scaled|rank|ranked)$",
    re.IGNORECASE,
)


def shadow_copies(spec: str, produces: list[str], columns: set[str]) -> list[str]:
    names = set(QUOTED.findall(spec)) - columns - set(produces)
    return sorted(
        name for name in names if COPY_SUFFIX.search(name) and COPY_SUFFIX.sub("", name) in columns
    )


def shadow_shortfall(found: dict[str, list[str]]) -> str | None:
    if not found:
        return None
    listed = "; ".join(f"{key}: {', '.join(names)}" for key, names in sorted(found.items()))
    return (
        "These options write a changed copy of a dataset column under a new name that their "
        "step does not produce, so the steps after them, which read the column's own name, "
        f"never see the change and the option has no effect: {listed}. Write the changed "
        "values into the column itself (for example clip 'campaign' in place), so that every "
        "later step reads them under the same name in every universe."
    )
