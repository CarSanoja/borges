from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Annotated

import typer

from borges.config import get_settings
from borges.identity.cli_actor import ActorError, resolve_actor
from borges.identity.run_scopes import scope_for_run
from borges.runs.models import RunRequest
from borges.runs.store import RunStore
from borges.runtime import audit
from borges.runtime.db import open_runtime_db
from borges.runtime.dead_letter import DeadLetters
from borges.runtime.schedules import ScheduleStore, parse_every

runs_app = typer.Typer(
    name="runs", help="Inspect and requeue runs held by the runtime.", no_args_is_help=True
)
schedule_app = typer.Typer(
    name="schedule", help="Re-run a case on a fixed interval.", no_args_is_help=True
)

KeyOption = Annotated[str | None, typer.Option("--key", envvar="BORGES_API_KEY")]


def _fail(message: str, code: int = 1) -> typer.Exit:
    typer.echo(message, err=True)
    return typer.Exit(code)


def _when(value: float | None) -> str:
    if value is None:
        return "never"
    return datetime.fromtimestamp(value, UTC).strftime("%Y-%m-%d %H:%M UTC")


@runs_app.command("dead-letter")
def dead_letter() -> None:
    """List the runs that exhausted their retries."""
    entries = DeadLetters(open_runtime_db(get_settings())).entries()
    for entry in entries:
        typer.echo(f"{entry.run_id}\t{entry.attempts} attempts\t{entry.error}")
    if not entries:
        typer.echo("the dead-letter queue is empty")


@runs_app.command()
def retry(run_id: Annotated[str, typer.Argument(help="A dead-lettered or failed run id")]) -> None:
    """Requeue a run; it resumes from its last checkpoint when a server or worker picks it up."""
    settings = get_settings()
    job = DeadLetters(open_runtime_db(settings)).requeue(run_id)
    if job is None:
        raise _fail(f"{run_id} is not a dead-lettered or failed run of the runtime", 2)
    store = RunStore(settings.borges_runs_dir)
    if store.exists(run_id):
        store.update_meta(run_id, status="queued")
    audit.record(settings, "runtime.run.requeue", principal="operator", data={"run_id": run_id})
    typer.echo(f"requeued {run_id}; `borges serve` or `borges runs work` will resume it")


@runs_app.command()
def work(
    wait: Annotated[float, typer.Option(help="Seconds to wait for the queue to drain")] = 3600.0,
) -> None:
    """Process the queued runs in this process until the queue is empty."""
    typer.echo(f"drained, {asyncio.run(_drain(wait))} run(s) still active")


async def _drain(wait: float) -> int:
    from borges.cases.registry import CaseRegistry
    from borges.runs.bus import EventBus
    from borges.runs.orchestrator import RunOrchestrator
    from borges.runtime.runtime import Runtime

    settings = get_settings()
    store = RunStore(settings.borges_runs_dir)
    bus = EventBus(store)
    orchestrator = RunOrchestrator(settings, store, bus, CaseRegistry(settings.borges_cases_dir))
    runtime = Runtime(settings, orchestrator, store, bus)
    await runtime.start()
    try:
        await runtime.drain(wait)
    finally:
        await runtime.stop()
    return len(runtime.queue.active_run_ids())


@schedule_app.command()
def add(
    case: Annotated[str, typer.Option("--case", help="Case id")],
    every: Annotated[str, typer.Option("--every", help="Interval such as 24h, 90m or 7d")],
    llm: Annotated[str | None, typer.Option(help="scripted or nebius")] = None,
    key: KeyOption = None,
    as_principal: Annotated[str | None, typer.Option("--as")] = None,
) -> None:
    """Store a schedule; the server submits it when BORGES_SCHEDULER=true."""
    settings = get_settings()
    if llm not in (None, "scripted", "nebius"):
        raise _fail("--llm must be scripted or nebius", 2)
    try:
        seconds = parse_every(every)
        request = RunRequest(case_id=case, llm=llm)  # type: ignore[arg-type]
        actor = resolve_actor(settings, scope_for_run(request, settings), key, as_principal, False)
    except (ValueError, ActorError) as error:
        raise _fail(str(error), 2) from None
    schedule = ScheduleStore(open_runtime_db(settings)).add(case, seconds, actor.principal_id, llm)
    audit.record(
        settings,
        "runtime.schedule.added",
        principal=actor.principal_id,
        data={"schedule_id": schedule.id, "case_id": case, "every_s": seconds},
    )
    typer.echo(f"{schedule.id}\t{case}\tevery {every}\tfirst run {_when(schedule.next_run)}")


@schedule_app.command("list")
def list_schedules() -> None:
    """Show every schedule and when it runs next."""
    entries = ScheduleStore(open_runtime_db(get_settings())).entries()
    for entry in entries:
        typer.echo(
            f"{entry.id}\t{entry.case_id}\tevery {int(entry.every_s)}s\t"
            f"next {_when(entry.next_run)}\tlast run {entry.last_run_id or 'none'}"
        )
    if not entries:
        typer.echo("no schedules")


@schedule_app.command()
def remove(schedule_id: Annotated[str, typer.Argument()]) -> None:
    """Delete a schedule."""
    if not ScheduleStore(open_runtime_db(get_settings())).remove(schedule_id):
        raise _fail(f"unknown schedule {schedule_id}", 2)
    typer.echo(f"removed {schedule_id}")
