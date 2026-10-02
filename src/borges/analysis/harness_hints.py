from __future__ import annotations

HINTS_SOURCE = """
    def _encoding_hint(exc, seen, kind):
        text = str(exc)
        if kind != "model" or not seen or "could not convert string to float" not in text:
            return ""
        frame = seen.get("frame")
        names = list(seen.get("nonnumeric", []))
        value = None
        if "'" in text:
            value = text.split("'", 1)[1].rsplit("'", 1)[0]
        holders = []
        if frame is not None and value is not None:
            for name in names:
                try:
                    if (frame[name].astype(str) == value).any():
                        holders.append(name)
                except Exception:
                    continue
        listed = [n for n in names if n in set(seen.get("ctx_lists", []))]
        found = holders or listed or names
        if not found:
            return ""
        return (
            " | non-numeric columns among the model inputs: " + repr(found[:30])
            + "; encode them with pd.get_dummies(..., drop_first=True, dtype=float) before"
            + " fitting, including every categorical covariate that comes from a ctx list"
        )
"""
