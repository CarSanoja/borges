from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

from borges.evaluation.calibration_data import CASE_DIR, make_dataset, to_parquet_bytes

SPEC = importlib.util.spec_from_file_location("gen", CASE_DIR / "generate.py")
gen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gen)


def test_default_build_matches_committed_bytes(tmp_path: Path) -> None:
    out = tmp_path / "data.parquet"
    gen.build().to_parquet(out, index=False, compression="zstd")
    assert out.read_bytes() == (CASE_DIR / "data.parquet").read_bytes()


def test_no_artefact_removes_internal_traffic() -> None:
    frame = make_dataset(3, 0.0, False, n_users=2000)
    assert not frame["is_internal"].any()
    assert frame["is_internal"].dtype == bool


def test_artefact_present_matches_case_share() -> None:
    frame = make_dataset(3, 0.0, True, n_users=6000)
    assert 0.005 < frame["is_internal"].mean() < 0.03
    internal = frame[frame["is_internal"]]
    assert internal["converted"].mean() > 0.4


def test_true_effect_moves_conversion() -> None:
    low = gen.build(5, true_effect=0.0, novelty_bump=0.0, internal_user_share=0.0, n_users=8000)
    high = gen.build(5, true_effect=0.03, novelty_bump=0.0, internal_user_share=0.0, n_users=8000)

    def lift(frame: pd.DataFrame) -> float:
        by = frame.groupby("variant")["converted"].mean()
        return float(by["treatment"] - by["control"])

    assert lift(high) - lift(low) > 0.015


def test_same_seed_is_deterministic_and_parquet_roundtrips() -> None:
    a = make_dataset(11, 0.005, True, n_users=1000)
    b = make_dataset(11, 0.005, True, n_users=1000)
    assert a.equals(b)
    assert len(to_parquet_bytes(a)) > 1000
