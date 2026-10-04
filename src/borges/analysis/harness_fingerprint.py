"""Fingerprint of a step's output frame and ctx, to tell steps that change nothing."""

from __future__ import annotations

FINGERPRINT_SOURCE = """
    def _fingerprint(out, ctx):
        import hashlib as _hashlib

        try:
            digest = _hashlib.sha1()
            digest.update(_json.dumps(list(map(str, out.columns))).encode())
            digest.update(_pd.util.hash_pandas_object(out, index=True).values.tobytes())
            digest.update(_json.dumps(ctx, sort_keys=True, default=str).encode())
            return digest.hexdigest()[:16]
        except Exception:
            return None
"""
