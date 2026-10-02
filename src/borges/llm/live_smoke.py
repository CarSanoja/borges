from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from borges.llm.client import DEFAULT_ROLE_MODELS, LLMError, ModelSpec, Role
from borges.llm.json_output import parse_model
from borges.llm.nebius_transport import (
    create_completion,
    estimate_prompt_tokens,
    with_schema_instructions,
)

SMOKE_CAP_USD = 0.05
SMOKE_MAX_TOKENS = 64


class Ping(BaseModel):
    ok: bool


class RoleReport(BaseModel):
    role: str
    model: str
    ok: bool
    error: str | None = None
    latency_s: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    finish_reason: str | None = None
    reasoning: bool = False


class SmokeReport(BaseModel):
    models_listed: list[str] = []
    missing_models: list[str] = []
    list_error: str | None = None
    roles: list[RoleReport] = []
    total_cost_usd: float = 0.0

    @property
    def ok(self) -> bool:
        return self.list_error is None and not self.missing_models and all(r.ok for r in self.roles)


def _reasoning_returned(message: Any) -> bool:
    for name in ("reasoning_content", "reasoning"):
        if getattr(message, name, None):
            return True
    extra = getattr(message, "model_extra", None) or {}
    if extra.get("reasoning_content") or extra.get("reasoning"):
        return True
    return "<think>" in (getattr(message, "content", None) or "")


async def check_models(client: Any, specs: dict[Role, ModelSpec], report: SmokeReport) -> None:
    try:
        page = await client.models.list()
        report.models_listed = sorted(str(m.id) for m in page.data)
    except Exception as exc:
        report.list_error = f"{type(exc).__name__}: {exc}"
        return
    wanted = sorted({spec.id for spec in specs.values()})
    report.missing_models = [m for m in wanted if m not in report.models_listed]


async def probe_role(
    client: Any, role: Role, spec: ModelSpec, spent: float, cap: float
) -> RoleReport:
    messages = with_schema_instructions(
        [{"role": "user", "content": 'Reply with {"ok": true}.'}], Ping
    )
    worst_case = spec.cost(estimate_prompt_tokens(messages), SMOKE_MAX_TOKENS)
    base = RoleReport(role=role.value, model=spec.id, ok=False)
    if spent + worst_case > cap:
        return base.model_copy(update={"error": f"cost cap ${cap:.2f} would be exceeded"})
    kwargs: dict[str, Any] = {
        "model": spec.id,
        "messages": messages,
        "max_tokens": SMOKE_MAX_TOKENS,
        "temperature": 0.0,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": spec.thinking}},
    }
    started = time.perf_counter()
    try:
        response = await create_completion(client, kwargs, Ping)
        choice = response.choices[0]
        text = choice.message.content or ""
        usage = response.usage
        tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
    except (LLMError, AttributeError, IndexError) as exc:
        return base.model_copy(
            update={"error": str(exc), "latency_s": time.perf_counter() - started}
        )
    update: dict[str, Any] = {
        "latency_s": time.perf_counter() - started,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": spec.cost(tokens_in, tokens_out),
        "finish_reason": getattr(choice, "finish_reason", None),
        "reasoning": _reasoning_returned(choice.message),
    }
    try:
        parse_model(text, Ping)
    except LLMError as exc:
        return base.model_copy(update={**update, "error": f"unparseable output: {exc}"})
    if update["reasoning"] and not spec.thinking:
        return base.model_copy(
            update={**update, "error": "reasoning content returned with thinking disabled"}
        )
    return base.model_copy(update={**update, "ok": True})


async def run_smoke(
    client: Any,
    role_models: dict[Role, ModelSpec] = DEFAULT_ROLE_MODELS,
    cap_usd: float = SMOKE_CAP_USD,
    progress: Callable[[str], None] = lambda _: None,
) -> SmokeReport:
    report = SmokeReport()
    await check_models(client, role_models, report)
    progress(f"models listed: {len(report.models_listed)}, missing: {report.missing_models}")
    for role, spec in role_models.items():
        item = await probe_role(client, role, spec, report.total_cost_usd, cap_usd)
        report.roles.append(item)
        report.total_cost_usd += item.cost_usd
        progress(f"{item.role}: {'ok' if item.ok else 'ERROR ' + str(item.error)}")
    return report


def render_report(report: SmokeReport) -> list[str]:
    lines = []
    if report.list_error:
        lines.append(f"GET /v1/models failed: {report.list_error}")
    else:
        lines.append(f"GET /v1/models: {len(report.models_listed)} models listed")
    for model in report.missing_models:
        lines.append(f"MISSING model id: {model}")
    for r in report.roles:
        status = "ok" if r.ok else f"ERROR {r.error}"
        lines.append(
            f"{r.role:<9} {r.model}  {status}  {r.latency_s:.2f}s  "
            f"in {r.tokens_in} / out {r.tokens_out}  ${r.cost_usd:.6f}  "
            f"finish={r.finish_reason}  reasoning={'yes' if r.reasoning else 'no'}"
        )
    lines.append(f"total cost: ${report.total_cost_usd:.6f}")
    lines.append("RESULT: " + ("PASS" if report.ok else "FAIL"))
    return lines
