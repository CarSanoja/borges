from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from borges.bench.blade_matcher import LLMMatcher, MissingReply
from borges.bench.blade_metrics import evaluate, mean_f1
from borges.bench.blade_rescore import CachedMatcher
from borges.llm.cache import DiskCache
from borges.llm.client import SUPER


class Replies:
    def __init__(self, text: str) -> None:
        self.text = text

    async def create(self, **kwargs):
        message = SimpleNamespace(content=self.text)
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


def live(text: str, cache: DiskCache) -> LLMMatcher:
    client = SimpleNamespace(chat=SimpleNamespace(completions=Replies(text)))
    return LLMMatcher(client, SUPER, cache)


async def test_cached_matcher_returns_what_the_live_matcher_stored(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    await live('{"A1-B1": {"similarity": 9}}', cache).match("model", "q", "s", ["ols"], ["ols fit"])
    cached = CachedMatcher(None, SUPER, cache)
    pairs = await cached.match("model", "q", "s", ["ols"], ["ols fit"])
    assert [(p.expert, p.agent) for p in pairs] == [(0, 0)]
    assert cached.usage.cached_calls == 1 and cached.usage.cost_usd == 0.0


async def test_a_reply_that_was_never_cached_is_missing_not_empty(tmp_path: Path) -> None:
    cached = CachedMatcher(None, SUPER, DiskCache(tmp_path))
    with pytest.raises(MissingReply):
        await cached.match("model", "q", "s", ["ols"], ["ols fit"])


async def test_evaluate_marks_the_kind_missing_and_withholds_the_mean(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    await live('{"A1-B1": {"similarity": 9}}', cache).match("cvar", "q", "s", ["IV: x"], ["IV: x"])
    cached = CachedMatcher(None, SUPER, cache)
    expert = {"cvar": ["IV: x"], "model": ["ols"], "transform": ["log y"]}
    runs = [{"cvar": ["IV: x"], "model": ["ols fit"], "transform": ["log y"]}]
    metrics = await evaluate(cached, "q", "s", expert, runs)
    assert metrics["cvar"]["coverage"] == 1.0
    assert "missing" in metrics["model"] and "coverage" not in metrics["model"]
    assert "missing" in metrics["transform"]
    assert mean_f1(metrics) is None


REAL = Path("evidence/blade/2026-10-03")
CLONE = Path(os.environ.get("BORGES_BLADE_DIR", "/nonexistent"))


@pytest.mark.skipif(
    not (REAL / "summary.json").is_file() or not CLONE.is_dir(),
    reason="needs the 2026-10-03 evidence folder and a BLADE clone",
)
async def test_tonights_run_rescores_offline_to_the_published_cvar_numbers() -> None:
    from borges.bench.blade_rescore import rescore

    cached = CachedMatcher(None, SUPER, DiskCache(REAL / "matcher-cache"))
    result = await rescore(REAL, cached, CLONE, ["soccer"])
    row = next(a for a in result.arms if a.arm == "adversary")
    published = next(
        r
        for r in json.loads((REAL / "summary.json").read_text())["rows"]
        if r["dataset"] == "soccer" and r["arm"] == "adversary"
    )
    assert round(row.metrics["cvar"]["coverage"], 4) == round(
        published["metrics"]["cvar"]["coverage"], 4
    )
