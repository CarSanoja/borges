from __future__ import annotations

import numpy as np
import pandas as pd

from borges.analysis.model_spec.schema import ModelSpecOutput

OUTCOMES = {
    "ols": "y_cont",
    "logit": "y_bin",
    "poisson": "y_count",
    "quasipoisson": "y_count",
    "negbin": "y_count",
}


def synthetic(seed: int = 7, rows: int = 400) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x = rng.integers(0, 2, rows).astype(float)
    m = rng.normal(size=rows)
    a = rng.normal(size=rows)
    games = rng.integers(1, 30, rows).astype(float)
    cat = rng.choice(["red", "green", "blue"], rows)
    group = rng.integers(0, 40, rows)
    shift = group % 5 * 0.1 + (cat == "red") * 0.3
    linear = 0.4 * x + 0.3 * m + 0.2 * x * m + 0.1 * a + shift
    frame = pd.DataFrame(
        {
            "x": x,
            "m": m,
            "a": a,
            "cat": cat,
            "g": group,
            "games": games,
            "y_cont": linear + rng.normal(size=rows),
            "y_bin": (rng.random(rows) < 1 / (1 + np.exp(-linear))).astype(float),
            "y_count": rng.negative_binomial(3, 3 / (3 + np.exp(0.5 + 0.3 * linear) * games / 10)),
        }
    )
    frame.loc[rng.choice(rows, 12, replace=False), "a"] = np.nan
    frame.loc[rng.choice(rows, 9, replace=False), "m"] = np.nan
    return frame


def make_spec(family: str, **fields: object) -> ModelSpecOutput:
    base: dict[str, object] = {
        "supported": True,
        "family": family,
        "outcome": OUTCOMES[family],
        "exposure": "x",
    }
    return ModelSpecOutput.model_validate({**base, **fields})
