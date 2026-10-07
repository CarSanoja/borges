from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from borges.cases.registry import CaseRegistry
from borges.config import REPO_ROOT, Settings
from borges.llm.client import UsageTotals
from borges.llm.factory import make_llm
from borges.runs.bus import EventBus
from borges.runs.inputs import resolve_run
from borges.runs.models import RunRequest, RunSnapshot
from borges.runs.orchestrator import RunOrchestrator
from borges.runs.store import RunStore


class CountingLLM:
    def __init__(self, inner: Any, calls: Counter[str]) -> None:
        self.inner = inner
        self.calls = calls
        self.totals: UsageTotals = inner.totals
        self.judges_defaults: bool = getattr(inner, "judges_defaults", True)

    async def complete(self, role: Any, messages: Any, **kwargs: Any) -> Any:
        self.calls[role.value] += 1
        return await self.inner.complete(role, messages, **kwargs)


def settings_for(tmp_path: Path, **extra: Any) -> Settings:
    return Settings(
        _env_file=None,
        nebius_api_key=None,
        borges_llm="scripted",
        borges_backend="local",
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=REPO_ROOT / "cases",
        **extra,
    )


class Bench:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = RunStore(settings.borges_runs_dir)
        self.calls: Counter[str] = Counter()

        def factory(config: Settings, mode: Any = None, **options: Any) -> CountingLLM:
            return CountingLLM(make_llm(config, mode, **options), self.calls)

        self.orchestrator = RunOrchestrator(
            settings,
            self.store,
            EventBus(self.store),
            CaseRegistry(settings.borges_cases_dir),
            llm_factory=factory,
        )

    async def run(
        self,
        run_id: str,
        case: str = "checkout_ab",
        principal: str | None = None,
        max_universes: int | None = None,
    ) -> tuple[RunSnapshot, Counter[str]]:
        self.calls.clear()
        request = RunRequest(
            case_id=case, llm="scripted", backend="local", max_universes=max_universes
        )
        if principal is not None:
            resolved = resolve_run(request, self.orchestrator.registry, self.settings)
            self.orchestrator.register(run_id, request, resolved, extra={"principal": principal})
        snapshot = await self.orchestrator.execute(run_id, request)
        return snapshot, Counter(self.calls)
