from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from borges import cli_runtime
from borges.bench.cli import bench_app
from borges.cli_audit import audit_app
from borges.cli_render import recording_label, summary_lines, universe_lines
from borges.config import Settings, get_settings
from borges.fleet.cli import agents_app
from borges.fleet.enforcement import RegistryBlocked
from borges.identity.chain_links import ChainBroken
from borges.identity.cli import keys_app
from borges.identity.key_material import ensure_keys
from borges.identity.key_notice import broken_message
from borges.identity.store_key import store_key
from borges.memory.cli import memory_app
from borges.runs.detail import build_universe_detail
from borges.runs.models import RunRequest, RunSnapshot
from borges.runs.orchestrator import new_run_id
from borges.runs.reproduce import reproduction_lines
from borges.runtime.cli import runs_app, schedule_app


class BorgesApp(typer.Typer):
    def __call__(self, *args: object, **kwargs: object) -> object:
        try:
            return super().__call__(*args, **kwargs)
        except ChainBroken as broken:
            held = store_key(get_settings())
            typer.echo(broken_message(broken.path, str(broken), held), err=True)
            raise SystemExit(1) from None


app = BorgesApp(name="borges", help="Walk the garden of forking analyses.", no_args_is_help=True)


@app.callback()
def load_keys() -> None:
    ensure_keys(get_settings())


app.add_typer(audit_app, name="audit")
app.add_typer(bench_app, name="bench")
app.add_typer(agents_app, name="agents")
app.add_typer(keys_app, name="keys")
app.add_typer(memory_app, name="memory")
app.add_typer(runs_app, name="runs")
app.add_typer(schedule_app, name="schedule")

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
    try:
        return asyncio.run(cli_runtime.execute_run(settings, run_id, request, record))
    except RegistryBlocked as blocked:
        typer.echo(str(blocked), err=True)
        raise typer.Exit(1) from blocked


@app.command()
def cases() -> None:
    """List the demo cases."""
    for card in cli_runtime.list_cases(get_settings()):
        recording = recording_label(card.has_scripted_recording, card.has_live_recording)
        typer.echo(f"{card.id}\t{card.title}\t{card.n_rows} rows\t{recording}")


@app.command()
def run(
    case: Annotated[str, typer.Option("--case", help="Case id")],
    llm: Annotated[str | None, typer.Option(help="scripted, nebius or local")] = None,
    backend: Annotated[str | None, typer.Option(help="local or contree")] = None,
    max_universes: Annotated[int | None, typer.Option(min=1, max=200)] = None,
    record: Annotated[bool, typer.Option(help="Record model responses as fixtures")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print the RunSnapshot")] = False,
    blind_notes: Annotated[
        bool, typer.Option("--blind-notes", help="Hide column notes and value descriptions")
    ] = False,
) -> None:
    """Execute a case in-process and print the outcome."""
    llm_mode = _validated(llm, ("scripted", "nebius", "local"), "--llm")
    backend_mode = _validated(backend, ("local", "contree"), "--backend")
    request = RunRequest(
        case_id=case,
        llm=llm_mode,
        backend=backend_mode,
        max_universes=max_universes,
        blind_notes=blind_notes,
    )
    snapshot = _run(get_settings(), request, record and llm_mode in ("nebius", "local"))
    if json_output:
        typer.echo(snapshot.model_dump_json(indent=2))
    else:
        typer.echo("\n".join(summary_lines(snapshot)))
    if snapshot.status != "completed":
        raise typer.Exit(1)


@app.command()
def replay(
    case: Annotated[str, typer.Option("--case", help="Case id")],
    source: Annotated[str, typer.Option(help="live or scripted")] = "live",
) -> None:
    """Print the outcome of a case's committed recording, without calling a model."""
    chosen = _validated(source, ("live", "scripted"), "--source") or "live"
    try:
        lines = cli_runtime.recording_lines(get_settings(), case, chosen)
    except FileNotFoundError as missing:
        typer.echo(str(missing), err=True)
        raise typer.Exit(1) from missing
    typer.echo("\n".join(lines))


@app.command()
def serve(
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option()] = 8000,
    reload: Annotated[bool, typer.Option(help="Auto-reload on code changes")] = False,
) -> None:
    """Serve the API and the built frontend."""
    import uvicorn

    from borges.telemetry.json_logging import configure_logging

    configure_logging()
    ensure_keys(get_settings())
    if reload:
        uvicorn.run(
            "borges.api.app:create_app",
            factory=True,
            host=host,
            port=port,
            reload=True,
            log_config=None,
        )
        return
    from borges.api.app import create_app

    uvicorn.run(create_app(), host=host, port=port, log_config=None)


@app.command("record-demo")
def record_demo(
    case: Annotated[str, typer.Option("--case", help="Case id")],
    llm: LlmOption = "scripted",
) -> None:
    """Run a case and store its event log as the offline recording."""
    llm_mode = _validated(llm, ("scripted", "nebius", "local"), "--llm")
    settings = get_settings()
    request = RunRequest(case_id=case, llm=llm_mode)
    snapshot = _run(settings, request, llm_mode in cli_runtime.LIVE_LLMS)
    if snapshot.status != "completed":
        typer.echo(f"run {snapshot.run_id} failed: {snapshot.error}", err=True)
        raise typer.Exit(1)
    target = cli_runtime.copy_recording(settings, snapshot.run_id, case, llm_mode)
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
    source: Annotated[str, typer.Option("--source", help="scripted or live")] = "scripted",
) -> None:
    """Re-execute one recorded universe on the case dataset and compare it to the recording."""
    _validated(source, ("scripted", "live"), "--source")
    try:
        plan, rep = asyncio.run(
            cli_runtime.reproduce_recorded(get_settings(), case, universe, source)
        )
    except (KeyError, FileNotFoundError) as error:
        typer.echo(str(error).strip("'\""), err=True)
        raise typer.Exit(1) from error
    typer.echo("\n".join(reproduction_lines(case, plan, rep)))
    if not rep.matches:
        raise typer.Exit(1)
