"""A step that rebuilds a column an earlier step built, refused at run time.

The candidates come from `rebuild_names.rebuilt_names` on the option's code. Only the harness
knows which columns arrived from earlier steps, which of those are raw data columns, and what
this step declares it produces; a column in none of the last two is the earlier step's work.
"""

from __future__ import annotations

REBUILD_SOURCE = """
    def _check_rebuilt(columns):
        rebuilt = [n for n in __REBUILDS__ if n in columns and n not in __PRODUCES__]
        if not rebuilt or not _os.path.exists("data.parquet"):
            return
        import pyarrow.parquet as _pq

        raw = set(_pq.read_schema("data.parquet").names)
        rebuilt = [n for n in rebuilt if n not in raw]
        if rebuilt:
            listed = ", ".join("'" + n + "'" for n in rebuilt)
            raise ValueError(
                "this code computes " + listed + " from scratch, but an earlier step built it and "
                "passed it on; recomputing it here throws away what that step did, such as rows "
                "it set by hand or the choice its options make. Read df[" + repr(rebuilt[0])
                + "] as it arrives instead of computing it again"
            )
"""
