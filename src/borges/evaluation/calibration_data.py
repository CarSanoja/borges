from __future__ import annotations

import importlib.util
import io
from pathlib import Path
from types import ModuleType

import pandas as pd

CASE_DIR = Path(__file__).resolve().parents[3] / "cases" / "checkout_ab"


def load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("checkout_ab_generate", CASE_DIR / "generate.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_dataset(
    seed: int,
    true_effect: float,
    artefact: bool,
    novelty_bump: float = 0.0,
    n_users: int | None = None,
) -> pd.DataFrame:
    generator = load_generator()
    return generator.build(
        seed,
        true_effect=true_effect,
        novelty_bump=novelty_bump,
        internal_user_share=generator.INTERNAL_USER_SHARE if artefact else 0.0,
        n_users=n_users or generator.N_USERS,
    )


def to_parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False, compression="zstd")
    return buffer.getvalue()
