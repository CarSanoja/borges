from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from borges.analysis import harness
from borges.analysis.models import AnalysisPlan, AnalysisResult, StepTrace
from borges.analysis.result_scale import convert
from borges.garden.executor_errors import failure_detail
from borges.garden.models import Universe, UniverseKind
from borges.garden.plausibility import implausible_message, is_implausible
from borges.garden.prefix_cache import Prefix, PrefixCache, PrefixNode
from borges.garden.reversal import find_reversal
from borges.runs.events import CheckpointCreatedData
from borges.sandbox.backend import BranchBackend, Checkpoint
from borges.telemetry.scopes import option_span

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]

STEP_TIMEOUT_S = 120.0


def universe_id(choices: dict[str, str]) -> str:
    canonical = json.dumps(sorted(choices.items()), separators=(",", ":"))
    return "u_" + hashlib.sha1(canonical.encode()).hexdigest()[:10]


class GardenExecutor:
    def __init__(
        self,
        backend: BranchBackend,
        plan: AnalysisPlan,
        data: bytes,
        emit: EmitFn | None = None,
        concurrency: int = 6,
        reuse_prefixes: bool = True,
        step_timeout_s: float = STEP_TIMEOUT_S,
    ) -> None:
        self.backend = backend
        self.plan = plan
        self.data = data
        self.emit = emit
        self.concurrency = concurrency
        self.reuse_prefixes = reuse_prefixes
        self.step_timeout_s = step_timeout_s
        self.baseline_verdict: str | None = None
        self.baseline_result: AnalysisResult | None = None
        self.root: Checkpoint | None = None
        self.baseline_checkpoints: list[str] = []
        self._cache = PrefixCache()
        self._semaphore = asyncio.Semaphore(concurrency)
        self._created = 0

    @property
    def checkpoints_created(self) -> int:
        return self._created

    async def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        if self.emit is not None:
            await self.emit(event_type, data)

    async def _emit_checkpoint(
        self,
        checkpoint: Checkpoint,
        step_id: str | None,
        option_id: str | None,
        depth: int,
        duration_s: float,
    ) -> None:
        self._created += 1
        payload = CheckpointCreatedData(
            checkpoint_id=checkpoint.id,
            parent_id=checkpoint.parent_id,
            step_id=step_id,
            option_id=option_id,
            depth=depth,
            duration_s=duration_s,
        )
        await self._emit("checkpoint.created", payload.model_dump(mode="json"))

    async def setup(self) -> Checkpoint:
        started = time.monotonic()
        self.root = await self.backend.root({harness.DATA_FILE: self.data})
        await self._emit_checkpoint(self.root, None, None, 0, time.monotonic() - started)
        return self.root

    async def _compute_prefix(
        self, parent: Checkpoint, index: int, step_id: str, option_id: str
    ) -> PrefixNode:
        step = self.plan.step(step_id)
        option = step.option(option_id)
        files = {
            harness.step_filename(step_id, option_id): harness.render_step(step, option).encode()
        }
        command = harness.step_command(step_id, option_id)
        try:
            run = await self.backend.run(
                parent, command, files=files, timeout_s=self.step_timeout_s
            )
        except Exception as exc:
            return PrefixNode(None, error=f"{step_id}/{option_id}: {exc}", cacheable=False)
        if not run.ok:
            detail, deterministic = failure_detail(run)
            return PrefixNode(
                None, error=f"{step_id}/{option_id}: {detail}", cacheable=deterministic
            )
        try:
            traces, result = harness.parse_output(run.stdout)
        except Exception as exc:
            return PrefixNode(None, error=f"{step_id}/{option_id}: unparseable output: {exc}")
        if result is not None:
            result, problem = convert(result, self.plan.result_scale)
            if problem is not None:
                return PrefixNode(None, error=f"{step_id}/{option_id}: {problem}")
        await self._emit_checkpoint(run.checkpoint, step_id, option_id, index + 1, run.duration_s)
        mine = [t for t in traces if t.step_id == step_id and t.option_id == option_id]
        if not mine:
            return PrefixNode(None, error=f"{step_id}/{option_id}: step produced no trace")
        return PrefixNode(run.checkpoint, traces=mine, result=result)

    async def _node(self, prefix: Prefix, parent: Checkpoint) -> PrefixNode:
        step_id, option_id, _ = prefix[-1]

        async def compute() -> PrefixNode:
            with option_span("step", step_id, option_id):
                return await self._compute_prefix(parent, len(prefix) - 1, step_id, option_id)

        if not self.reuse_prefixes:
            return await compute()
        return await self._cache.get_or_compute(prefix, compute)

    async def _walk(
        self, choices: dict[str, str]
    ) -> tuple[list[str], list[StepTrace], AnalysisResult | None, str | None]:
        assert self.root is not None
        parent = self.root
        checkpoints: list[str] = []
        traces: list[StepTrace] = []
        result: AnalysisResult | None = None
        prefix: Prefix = ()
        for step in self.plan.steps:
            option = step.option(choices[step.id])
            digest = hashlib.sha1((option.code or "").encode()).hexdigest()[:12]
            prefix = (*prefix, (step.id, option.id, digest))
            node = await self._node(prefix, parent)
            if not node.ok or node.checkpoint is None:
                return checkpoints, traces, None, node.error
            parent = node.checkpoint
            checkpoints.append(parent.id)
            traces.extend(node.traces)
            result = node.result
        if result is None:
            return checkpoints, traces, None, "final step produced no result"
        return checkpoints, traces, result, None

    def _flips(self, result: AnalysisResult) -> bool:
        return self.plan.decision_rule.label(result) != self.baseline_verdict

    async def run_universe(self, choices: dict[str, str], kind: UniverseKind) -> Universe:
        if self.root is None:
            raise RuntimeError("GardenExecutor.setup() must be called before run_universe()")
        full = {**self.plan.default_choices(), **choices}
        changed = [s.id for s in self.plan.steps if full[s.id] != s.default.id]
        universe = Universe(
            id=universe_id(full), choices=full, changed=changed, kind=kind, status="running"
        )
        async with self._semaphore:
            await self._emit("universe.started", {"universe": universe.model_dump(mode="json")})
            started = time.monotonic()
            try:
                checkpoints, traces, result, error = await self._walk(full)
            except Exception as exc:
                checkpoints, traces, result, error = [], [], None, f"{type(exc).__name__}: {exc}"
            universe = universe.model_copy(update={"checkpoints": checkpoints, "traces": traces})
            if (
                result is not None
                and kind != "baseline"
                and self.baseline_result is not None
                and is_implausible(self.baseline_result, result)
            ):
                error = implausible_message(self.baseline_result, result)
                result = None
            if result is not None and kind != "baseline" and self.baseline_checkpoints:
                assert self.root is not None
                reason = await find_reversal(
                    self.backend,
                    self.plan,
                    self.root.id,
                    self.baseline_checkpoints,
                    checkpoints,
                    full,
                )
                if reason is not None:
                    error = reason
                    result = None
            if result is None:
                universe.status = "failed"
                universe.error = error
            else:
                verdict = self.plan.decision_rule.label(result)
                if kind == "baseline":
                    self.baseline_verdict = verdict
                    self.baseline_result = result
                    self.baseline_checkpoints = checkpoints
                universe.status = "done"
                universe.result = result
                universe.verdict = verdict
                universe.flipped = kind != "baseline" and verdict != self.baseline_verdict
            universe.duration_s = time.monotonic() - started
            await self._emit("universe.finished", {"universe": universe.model_dump(mode="json")})
        return universe
