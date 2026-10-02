from __future__ import annotations

from typing import Annotated

import typer

from borges.config import Settings, get_settings
from borges.fleet.fleet import build_fleet
from borges.fleet.governance import change_state, publish_audited
from borges.fleet.locations import SEED_ACTOR, open_store, seed_store
from borges.fleet.models import Approval
from borges.fleet.store import RegistryStore, TransitionError

agents_app = typer.Typer(
    name="agents", help="Publish, version and approve the agent registry.", no_args_is_help=True
)

SeedOption = Annotated[
    bool, typer.Option("--seed", help="Operate on the tracked seed store instead of BORGES_HOME")
]


def _target(seed: bool) -> tuple[RegistryStore, Settings | None, str]:
    if seed:
        return seed_store(), None, SEED_ACTOR
    settings = get_settings()
    return open_store(settings), settings, "operator"


@agents_app.command("list")
def list_agents(seed: SeedOption = False) -> None:
    """Show every agent with its version and approval state."""
    store, settings, _ = _target(seed)
    fleet = build_fleet(settings or get_settings())
    for descriptor in fleet.agents:
        record = store.by_definition(descriptor.agent_id, descriptor.definition_sha)
        version = f"{record.version} {record.state}" if record else "unpublished"
        typer.echo(
            f"{descriptor.agent_id}\t{descriptor.lifecycle}\t{version}\t{descriptor.model_id}"
        )
    typer.echo(f"registry_sha {fleet.registry_sha}")


@agents_app.command()
def publish(
    seed: SeedOption = False,
    message: Annotated[str | None, typer.Option("--message", "-m")] = None,
    approve: Annotated[bool, typer.Option("--approve", help="Approve what was published")] = False,
) -> None:
    """Record a new version for every agent whose definition changed."""
    store, settings, actor = _target(seed)
    fleet = build_fleet(settings or get_settings())
    published = publish_audited(store, fleet, settings, actor, message)
    if not published:
        typer.echo("nothing to publish: every definition matches its last published version")
        return
    for item in published:
        typer.echo(f"published {item.agent_id} {item.version} ({item.bump}): {item.changelog}")
        if approve:
            change_state(store, item.agent_id, item.version, "approved", settings, actor)
            typer.echo(f"approved {item.agent_id} {item.version}")


def _transition(agent_id: str, version: str, to: Approval, seed: bool, reason: str | None) -> None:
    store, settings, actor = _target(seed)
    try:
        record = change_state(store, agent_id, version, to, settings, actor, reason)
    except KeyError:
        typer.echo(f"unknown version {agent_id} {version}", err=True)
        raise typer.Exit(2) from None
    except TransitionError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from None
    typer.echo(f"{record.agent_id} {record.version} is now {record.state}")


@agents_app.command()
def approve(
    agent_id: str,
    version: str,
    seed: SeedOption = False,
    reason: Annotated[str | None, typer.Option("--reason")] = None,
) -> None:
    """Approve a proposed version."""
    _transition(agent_id, version, "approved", seed, reason)


@agents_app.command()
def retire(
    agent_id: str,
    version: str,
    seed: SeedOption = False,
    reason: Annotated[str | None, typer.Option("--reason")] = None,
) -> None:
    """Retire a version so it no longer satisfies enforcement."""
    _transition(agent_id, version, "retired", seed, reason)
