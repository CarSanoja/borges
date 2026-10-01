from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 137
N_USERS = 16000
BASE_RATE = 0.0275
TRUE_EFFECT = -0.0020
NOVELTY_BUMP = 0.004
INTERNAL_USER_SHARE = 0.0115
INTERNAL_TREATMENT_SHARE = 0.80
INTERNAL_RATE = 0.58
BOT_SHARE = 0.03
PLATFORM_MULTIPLIER = {"web": 1.0, "ios": 1.15, "android": 0.8}
OUT = Path(__file__).parent / "data.parquet"


def build(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    sessions_per_user = rng.choice([1, 2, 3, 4], size=N_USERS, p=[0.45, 0.30, 0.17, 0.08])
    internal_user = rng.random(N_USERS) < INTERNAL_USER_SHARE
    treated_user = np.where(
        internal_user,
        rng.random(N_USERS) < INTERNAL_TREATMENT_SHARE,
        rng.random(N_USERS) < 0.5,
    )
    platform_user = rng.choice(["web", "ios", "android"], size=N_USERS, p=[0.55, 0.30, 0.15])

    idx = np.repeat(np.arange(N_USERS), sessions_per_user)
    n = len(idx)
    treated = treated_user[idx]
    internal = internal_user[idx]
    platform = platform_user[idx]
    day = rng.integers(0, 14, size=n)
    bot = (rng.random(n) < BOT_SHARE) & ~internal

    seconds = rng.lognormal(mean=4.4, sigma=0.9, size=n)
    seconds = np.where(bot, rng.uniform(0.2, 1.9, size=n), np.maximum(seconds, 2.0))

    multiplier = pd.Series(platform).map(PLATFORM_MULTIPLIER).to_numpy()
    prob = BASE_RATE * multiplier + TRUE_EFFECT * treated
    prob = prob + NOVELTY_BUMP * (treated & (day <= 2))
    prob = np.where(internal, INTERNAL_RATE, prob)
    prob = np.where(bot, 0.0, prob)
    converted = (rng.random(n) < prob).astype(np.int8)

    revenue = np.round(rng.lognormal(mean=3.9, sigma=0.6, size=n), 2) * converted
    frame = pd.DataFrame(
        {
            "session_id": np.arange(1, n + 1),
            "user_id": idx + 1,
            "day": day.astype(np.int8),
            "variant": np.where(treated, "treatment", "control"),
            "platform": platform,
            "is_internal": internal,
            "session_seconds": seconds.round(2).astype(np.float32),
            "converted": converted,
            "revenue": revenue.astype(np.float32),
        }
    )
    return frame


def main() -> None:
    frame = build()
    frame.to_parquet(OUT, index=False, compression="zstd")
    print(f"{len(frame)} sessions, {OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
