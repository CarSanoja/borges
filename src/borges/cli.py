from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from borges import cli_runtime
from borges.cli_render import summary_lines, universe_lines
from borges.config import Settings, get_settings
from borges.runs.detail import build_universe_detail
from borges.runs.models import RunRequest, RunSnapshot
from borges.runs.orchestrator import new_run_id
from borges.runs.reproduce import reproduction_lines

app = typer.Typer(name="borges", help="Walk the garden of forking analyses.", no_args_is_help=True)

LlmOption = Annotated[str, typer.Option("--llm", help="scripted, nebius or local")]


def _validated(value: str | None, allowed: tuple[str, ...], name: str) -> str | None:
    if value is not None and value not in allowed:
        raise typer.BadParameter(f"{name} must be one of {', '.join(allowed)}")
    return value


def _run(
    settings: Settings,
    request: RunRequest,
    record: bool,
) -> RunSnapshot:
    run_id = new_run_id()
    return asyncio.run(cli_runtime.execute_run(settings, run_id, request, record))


@app.command()
def cases() -> None:
    """List the demo cases."""
    for card in cli_runtime.list_cases(get_settings()):
        recording = "recorded" if card.has_recording else "no recording"
        typer.echo(f"{card.id}\t{card.title}\t{card.n_rows} rows\t{recording}")


@app.command()
def run(
    case: Annotated[str, typer.Option("--case", help="Case id")],
    llm: Annotated[str | None, typer.Option(help="scripted, nebius or local")] = None,
    backend: Annotated[str | None, typer.Option(help="local or contree")] = None,
    max_universes: Annotated[int | None, typer.Option(min=1, max=200)] = None,
    record: Annotated[bool, typer.Option(help="Record model responses as fixtures")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print the RunSnapshot")] = False,
) -> None:
    """Execute a case in-process and print the outcome."""
    llm_mode = _validated(llm, ("scripted", "nebius", "local"), "--llm")
    backend_mode = _validated(backend, ("local", "contree"), "--backend")
    request = RunRequest(
        case_id=case,
        llm=llm_mode,
        backend=backend_mode,
        max_universes=max_universes,
    )
    snapshot = _run(get_settings(), request, record and llm_mode in ("nebius", "local"))
    if json_output:
        typer.echo(snapshot.model_dump_json(indent=2))
    else:
        typer.echo("\n".join(summary_lines(snapshot)))
    if snapshot.status != "completed":
        raise typer.Exit(1)


@app.command()
def serve(
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option()] = 8000,
    reload: Annotated[bool, typer.Option(help="Auto-reload on code changes")] = False,
) -> None:
    """Serve the API and the built frontend."""
    import uvicorn

    if reload:
        uvicorn.run("borges.api.app:create_app", factory=True, host=host, port=port, reload=True)
        return
    from borges.api.app import create_app

    uvicorn.run(create_app(), host=host, port=port)


@app.command("record-demo")
def record_demo(
    case: Annotated[str, typer.Option("--case", help="Case id")],
    llm: LlmOption = "scripted",
) -> None:
    """Run a case and store its event log as the offline recording."""
    llm_mode = _validated(llm, ("scripted", "nebius", "local"), "--llm")
    settings = get_settings()
    request = RunRequest(case_id=case, llm=llm_mode)
    snapshot = _run(settings, request, llm_mode in ("nebius", "local"))
    if snapshot.status != "completed":
        typer.echo(f"run {snapshot.run_id} failed: {snapshot.error}", err=True)
        raise typer.Exit(1)
    target = cli_runtime.copy_recording(settings, snapshot.run_id, case)
    typer.echo(f"recorded {snapshot.run_id} -> {target}")


@app.command()
def universe(run_id: str, universe_id: str) -> None:
    """Print the detail of one universe of a stored run."""
    try:
        snapshot = cli_runtime.load_snapshot(get_settings(), run_id)
        detail = build_universe_detail(snapshot, universe_id)
    except (KeyError, FileNotFoundError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo("\n".join(universe_lines(detail)))


@app.command()
def reproduce(
    case: Annotated[str, typer.Option("--case", help="Case id")],
    universe: Annotated[str, typer.Option("--universe", help="Universe id from the recording")],
) -> None:
    """Re-execute one recorded universe on the case dataset and compare it to the recording."""
    try:
        plan, rep = asyncio.run(cli_runtime.reproduce_recorded(get_settings(), case, universe))
    except (KeyError, FileNotFoundError) as error:
        typer.echo(str(error).strip("'\""), err=True)
        raise typer.Exit(1) from error
    typer.echo("\n".join(reproduction_lines(case, plan, rep)))
    if not rep.matches:
        raise typer.Exit(1)
