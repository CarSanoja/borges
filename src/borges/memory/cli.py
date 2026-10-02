from __future__ import annotations

from typing import Annotated

import typer

from borges.config import get_settings
from borges.memory import service
from borges.memory.factory import open_repository
from borges.memory.repository import MemoryUnavailable

memory_app = typer.Typer(
    name="memory", help="Inspect, annotate and erase what Borges remembers.", no_args_is_help=True
)

TenantOption = Annotated[str, typer.Option("--tenant", help="Tenant name, or public-demo")]
DatasetOption = Annotated[str | None, typer.Option("--dataset", help="Dataset fingerprint")]


@memory_app.command("list")
def list_memory(tenant: TenantOption) -> None:
    """Show how many memories a tenant holds per dataset and kind; never payloads."""
    repo = open_repository(get_settings())
    try:
        rows = repo.counts(tenant)
    finally:
        repo.close()
    for row in rows:
        typer.echo(
            f"{row['dataset']}\tverdict={row['verdict']}\tcode={row['code']}"
            f"\tadversary={row['adversary']}\tnote={row['note']}"
        )
    if not rows:
        typer.echo(f"{tenant} holds no memories")


@memory_app.command()
def forget(tenant: TenantOption, dataset: DatasetOption = None) -> None:
    """Erase a tenant's memories, all of them or those of one dataset, and audit the erasure."""
    removed = service.forget(get_settings(), "operator", tenant, dataset)
    scope = f"dataset {dataset}" if dataset else "every dataset"
    typer.echo(f"forgot {sum(removed.values())} memories of {tenant} for {scope}")


@memory_app.command()
def note(
    tenant: TenantOption,
    dataset: Annotated[str, typer.Option("--dataset", help="Dataset fingerprint")],
    column: Annotated[str, typer.Option("--column", help="Column the note is about")],
    text: Annotated[str, typer.Argument(help="What the column means or its known caveat")],
) -> None:
    """Add an owner note the planner reads for this dataset."""
    try:
        service.add_note(get_settings(), "operator", tenant, dataset, column, text)
    except (ValueError, MemoryUnavailable) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"noted {column} for {tenant}")


@memory_app.command()
def fingerprint(case: Annotated[str, typer.Option("--case", help="Curated case id")]) -> None:
    """Print the dataset fingerprint of a curated case, the key of its memories."""
    from borges.analysis.profile import profile_dataframe
    from borges.cases.registry import CaseRegistry
    from borges.memory.signatures import dataset_fingerprint
    from borges.runs.pipeline_data import load_dataframe

    settings = get_settings()
    registry = CaseRegistry(settings.borges_cases_dir)
    frame = load_dataframe(registry.data_bytes(case))
    profile = profile_dataframe(frame, case)
    typer.echo(dataset_fingerprint(profile))
