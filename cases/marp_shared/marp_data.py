from __future__ import annotations

import urllib.request
from pathlib import Path

import pandas as pd

SHARED_DIR = Path(__file__).resolve().parent
RAW_DIR = SHARED_DIR.parents[1] / "data" / "raw"
DATA_URL = "https://osf.io/download/k9puq/"
TEAMS_URL = "https://osf.io/download/bw863/"
CODING_URL = "https://osf.io/download/g9sfm/"
DATA_CSV = "MARP_data.csv"
TEAMS_CSV = "MARP_data_main.csv"
CODING_CSV = "MARP_variable_coding.csv"

REL_ITEMS = [f"rel_{i}" for i in range(1, 10)]
NORM_ITEMS = ["cnorm_1", "cnorm_2"]
WB_ITEMS = (
    ["wb_gen_1", "wb_gen_2"]
    + [f"wb_phys_{i}" for i in range(1, 8)]
    + [f"wb_psych_{i}" for i in range(1, 7)]
    + [f"wb_soc_{i}" for i in range(1, 4)]
)
WB_MEANS = ["wb_overall_mean", "wb_phys_mean", "wb_psych_mean", "wb_soc_mean"]
DEMOGRAPHICS = ["age", "gender", "ses", "education", "gdp_scaled", "attention_check"]
COLUMNS = ["country", *REL_ITEMS, *NORM_ITEMS, *WB_ITEMS, *WB_MEANS, *DEMOGRAPHICS]


def fetch_cached(url: str, filename: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_DIR / filename
    if not target.exists():
        request = urllib.request.Request(url, headers={"User-Agent": "borges-case-builder"})
        with urllib.request.urlopen(request, timeout=120) as response:
            target.write_bytes(response.read())
    return target


def compact(raw: pd.DataFrame) -> pd.DataFrame:
    out = raw[COLUMNS].copy()
    out["country"] = out["country"].astype("category")
    out["gender"] = out["gender"].astype("category")
    out["attention_check"] = out["attention_check"].astype("int8")
    for name in out.columns:
        if name not in ("country", "gender", "attention_check"):
            out[name] = out[name].astype("float32")
    return out


def load_compact() -> pd.DataFrame:
    return compact(pd.read_csv(fetch_cached(DATA_URL, DATA_CSV)))


def write_dataset(case_dirs: list[Path]) -> None:
    frame = load_compact()
    for case_dir in case_dirs:
        target = case_dir / "data.parquet"
        frame.to_parquet(target, index=False, compression="zstd")
        print(f"wrote {target} rows={len(frame)} bytes={target.stat().st_size}")
