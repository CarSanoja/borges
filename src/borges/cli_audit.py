from __future__ import annotations

from typing import Annotated

import typer

from borges.config import get_settings
from borges.runs.store import RunStore
from borges.telemetry.audit_verify import verify_chain
from borges.telemetry.run_telemetry import global_audit_path, run_audit_path

audit_app = typer.Typer(
    name="audit", help="Inspect the hash-chained audit logs.", no_args_is_help=True
)


@audit_app.command("verify")
def verify(
    target: Annotated[str, typer.Argument(help="A run id, or 'global'")],
) -> None:
    """Recompute the audit chain and report the first broken link."""
    settings = get_settings()
    if target == "global":
        path = global_audit_path(settings)
    elif RunStore(settings.borges_runs_dir).exists(target):
        path = run_audit_path(settings, target)
    else:
        typer.echo(f"unknown run '{target}'", err=True)
        raise typer.Exit(2)
    report = verify_chain(path)
    if not report.exists:
        typer.echo(f"no audit log at {path}")
        raise typer.Exit(2)
    if report.ok:
        typer.echo(f"OK {report.records} records head={report.head_hash} {path}")
        return
    typer.echo(
        f"BROKEN at seq {report.broken_seq} (line {report.broken_line}): {report.reason}; "
        f"{report.records} records verified before it; {path}"
    )
    raise typer.Exit(1)
