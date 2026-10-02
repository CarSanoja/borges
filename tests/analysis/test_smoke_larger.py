from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis import coder_smoke
from borges.analysis.coder_smoke import SmokeConfig, smoke_plan
from borges.analysis.models import AnalysisPlan
from borges.analysis.smoke_larger import is_singular_error, larger_sample
from borges.llm.client import LLMError
from borges.sandbox.local_backend import LocalBackend
from tests.analysis.fakes import make_plan

ROWS = 8000
LEVELS = 300
KEEP = "def apply(df, ctx):\n    return df.copy()"
TWO_WAY = (
    "import numpy as np\n"
    "import pandas as pd\n\n"
    "def estimate(df, ctx):\n"
    '    X = pd.get_dummies(df[["a", "b"]].astype(str), drop_first=True, dtype=float)\n'
    "    X.insert(0, 'const', 1.0)\n"
    "    if np.linalg.matrix_rank(X.to_numpy()) < X.shape[1]:\n"
    '        raise np.linalg.LinAlgError("Singular matrix")\n'
    '    return {"estimate": 0.3, "ci_low": 0.1, "ci_high": 0.5, "p_value": 0.01, "n": len(df)}\n'
)
ALWAYS_SINGULAR = (
    "import numpy as np\n\n"
    "def estimate(df, ctx):\n"
    '    raise np.linalg.LinAlgError("Singular matrix")\n'
)
OTHER_ERROR = "def estimate(df, ctx):\n    raise KeyError('missing')\n"


def dataset(rows: int = ROWS) -> bytes:
    rng = np.random.default_rng(3)
    frame = pd.DataFrame(
        {
            "a": rng.integers(0, LEVELS, rows),
            "b": rng.integers(0, LEVELS, rows),
            "y": rng.normal(size=rows),
        }
    )
    buffer = io.BytesIO()
    frame.to_parquet(buffer)
    return buffer.getvalue()


def plan_with(code: str) -> AnalysisPlan:
    plan = make_plan(with_code=True)
    plan.step("d1").options = [plan.step("d1").option("keep")]
    plan.step("d1").option("keep").code = KEEP
    plan.step("m1").options = [plan.step("m1").option("ols")]
    plan.step("m1").option("ols").code = code
    return plan


class Repairs:
    def __init__(self) -> None:
        self.errors: list[str] = []

    async def __call__(self, step, option, error, attempt):
        self.errors.append(error)
        raise LLMError("no repair expected")


async def smoke(tmp_path: Path, code: str, data: bytes, repairs: Repairs | None = None):
    events: list[tuple] = []

    async def on_smoke(*args):
        events.append(args)

    config = SmokeConfig(LocalBackend(tmp_path), data, on_smoke)
    await smoke_plan(config, plan_with(code), repairs or Repairs())
    return events, config


def test_singular_error_detection() -> None:
    assert is_singular_error("numpy.linalg.LinAlgError: Singular matrix")
    assert is_singular_error("Design matrix is singular")
    assert is_singular_error("perfect collinearity detected")
    assert is_singular_error("PerfectSeparationError: Perfect separation detected")
    assert not is_singular_error("KeyError: 'missing'")
    assert not is_singular_error(None)


def test_larger_sample_is_capped_and_deterministic() -> None:
    data, rows = larger_sample(dataset(), 1000)
    again, _ = larger_sample(dataset(), 1000)
    assert rows == 1000 and data == again
    whole, total = larger_sample(dataset(), 50000)
    assert total == ROWS and whole == dataset()


async def test_singular_on_the_sample_passes_on_a_larger_one(tmp_path: Path) -> None:
    events, _ = await smoke(tmp_path, TWO_WAY, dataset())
    model = next(e for e in events if e[0] == "m1")
    assert model[2:5] == ("passed", 1, None)
    assert model[6] == ROWS


async def test_without_the_retry_the_same_model_would_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Off:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def rerun(self, step, option):
            return None

    monkeypatch.setattr(coder_smoke, "LargerSample", Off)
    repairs = Repairs()
    with pytest.raises(LLMError):
        await smoke(tmp_path, TWO_WAY, dataset(), repairs)
    assert "Singular matrix" in repairs.errors[0]


async def test_still_singular_on_the_larger_sample_asks_for_a_repair(tmp_path: Path) -> None:
    repairs = Repairs()
    with pytest.raises(LLMError):
        await smoke(tmp_path, ALWAYS_SINGULAR, dataset(), repairs)
    assert "Singular matrix" in repairs.errors[0]


async def test_other_errors_are_not_retried(tmp_path: Path) -> None:
    repairs = Repairs()
    with pytest.raises(LLMError):
        await smoke(tmp_path, OTHER_ERROR, dataset(), repairs)
    assert "missing" in repairs.errors[0]


async def test_no_retry_when_the_data_is_already_the_sample(tmp_path: Path) -> None:
    config = SmokeConfig(LocalBackend(tmp_path), dataset(150))
    with pytest.raises(LLMError):
        await smoke_plan(config, plan_with(ALWAYS_SINGULAR), Repairs())
    assert config.larger is not None and config.larger.rows is None
