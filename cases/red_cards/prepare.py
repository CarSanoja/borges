from __future__ import annotations

import io
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

CASE_DIR = Path(__file__).resolve().parent
RAW_DIR = CASE_DIR.parents[1] / "data" / "raw"
DATASET_URL = "https://osf.io/download/fv8c3/"
TEAMS_URL = "https://osf.io/download/fa743/"
DATASET_ZIP = "crowdstorming_dyads.zip"
TEAMS_CSV = "crowdsourcing_effects_in_or.csv"
CSV_NAME = "CrowdstormingDataJuly1st.csv"

COLUMNS = [
    "playerShort",
    "refNum",
    "refCountry",
    "games",
    "redCards",
    "yellowCards",
    "yellowReds",
    "rater1",
    "rater2",
    "position",
    "leagueCountry",
    "height",
    "weight",
    "meanIAT",
    "meanExp",
]


def fetch_cached(url: str, filename: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_DIR / filename
    if not target.exists():
        request = urllib.request.Request(url, headers={"User-Agent": "borges-case-builder"})
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
        target.write_bytes(payload)
    return target


def load_dyads() -> pd.DataFrame:
    archive = fetch_cached(DATASET_URL, DATASET_ZIP)
    with zipfile.ZipFile(archive) as zf:
        raw = pd.read_csv(io.BytesIO(zf.read(CSV_NAME)), usecols=COLUMNS)
    return raw


def compact(raw: pd.DataFrame) -> pd.DataFrame:
    out = raw[COLUMNS].copy()
    out["playerShort"] = out["playerShort"].astype("category")
    out["position"] = out["position"].astype("category")
    out["leagueCountry"] = out["leagueCountry"].astype("category")
    for name in ("refNum", "refCountry", "games", "redCards", "yellowCards", "yellowReds"):
        out[name] = out[name].astype("int32")
    for name in ("rater1", "rater2", "height", "weight", "meanIAT", "meanExp"):
        out[name] = out[name].astype("float32")
    return out


def load_teams() -> pd.DataFrame:
    return pd.read_csv(fetch_cached(TEAMS_URL, TEAMS_CSV))


def main() -> None:
    frame = compact(load_dyads())
    target = CASE_DIR / "data.parquet"
    frame.to_parquet(target, index=False, compression="zstd")
    print(f"wrote {target} rows={len(frame)} bytes={target.stat().st_size}")


if __name__ == "__main__":
    main()
