from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Annotated

import typer

from borges.config import Settings, get_settings
from borges.fleet.fleet import build_fleet
from borges.fleet.governance import FourEyesViolation, change_state, publish_audited
from borges.fleet.locations import SEED_ACTOR, open_store, seed_store, store_path
from borges.fleet.models import Approval
from borges.fleet.store import RegistryStore, RegistryTampered, TransitionError
from borges.identity.cli_actor import ActorError, resolve_actor
from borges.identity.scopes import REGISTRY_APPROVE, REGISTRY_PUBLISH

agents_app = typer.Typer(
    name="agents", help="Publish, version and approve the agent registry.", no_args_is_help=True
)

SeedOption = Annotated[
    bool, typer.Option("--seed", help="Operate on the tracked seed store instead of BORGES_HOME")
]


KeyOption = Annotated[
    str | None,
    typer.Option("--key", envvar="BORGES_API_KEY", help="API key (bk_...) of the acting principal"),
]
AsOption = Annotated[str | None, typer.Option("--as", help="Principal the action is recorded as")]


def _guarded(command: Callable[..., None]) -> Callable[..., None]:
    @wraps(command)
    def run(*args: object, **kwargs: object) -> None:
        try:
            command(*args, **kwargs)
        except RegistryTampered as broken:
            typer.echo(str(broken), err=True)
            raise typer.Exit(1) from None
        except (ActorError, FourEyesViolation) as denied:
            typer.echo(str(denied), err=True)
            raise typer.Exit(1) from None

    return run


def _target(
    seed: bool,
    scope: str,
    key: str | None = None,
    as_principal: str | None = None,
    mutating: bool = True,
) -> tuple[RegistryStore, Settings | None, str]:
    if seed:
        return seed_store(), None, SEED_ACTOR
    settings = get_settings()
    needs_key = settings.borges_registry_four_eyes and mutating
    actor = resolve_actor(settings, scope, key, as_principal, needs_key)
    return open_store(settings), settings, actor.principal_id


@agents_app.command("list")
@_guarded
def list_agents(seed: SeedOption = False) -> None:
    """Show every agent with its version and approval state."""
    store, settings, _ = _target(seed, REGISTRY_PUBLISH, mutating=False)
    fleet = build_fleet(settings or get_settings())
    for descriptor in fleet.agents:
        record = store.by_definition(descriptor.agent_id, descriptor.definition_sha)
        version = f"{record.version} {record.state}" if record else "unpublished"
        typer.echo(
            f"{descriptor.agent_id}\t{descriptor.lifecycle}\t{version}\t{descriptor.model_id}"
        )
    typer.echo(f"registry_sha {fleet.registry_sha}")


@agents_app.command()
@_guarded
def publish(
    seed: SeedOption = False,
    key: KeyOption = None,
    as_principal: AsOption = None,
    message: Annotated[str | None, typer.Option("--message", "-m")] = None,
    approve: Annotated[bool, typer.Option("--approve", help="Approve what was published")] = False,
) -> None:
    """Record a new version for every agent whose definition changed."""
    store, settings, actor = _target(seed, REGISTRY_PUBLISH, key, as_principal)
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


def _transition(
    agent_id: str,
    version: str,
    to: Approval,
    seed: bool,
    reason: str | None,
    key: str | None,
    as_principal: str | None,
) -> None:
    store, settings, actor = _target(seed, REGISTRY_APPROVE, key, as_principal)
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
@_guarded
def approve(
    agent_id: str,
    version: str,
    seed: SeedOption = False,
    reason: Annotated[str | None, typer.Option("--reason")] = None,
    key: KeyOption = None,
    as_principal: AsOption = None,
) -> None:
    """Approve a proposed version (four-eyes mode needs a registry:approve key)."""
    _transition(agent_id, version, "approved", seed, reason, key, as_principal)


@agents_app.command()
@_guarded
def retire(
    agent_id: str,
    version: str,
    seed: SeedOption = False,
    reason: Annotated[str | None, typer.Option("--reason")] = None,
    key: KeyOption = None,
    as_principal: AsOption = None,
) -> None:
    """Retire a version so it no longer satisfies enforcement."""
    _transition(agent_id, version, "retired", seed, reason, key, as_principal)


@agents_app.command()
def verify(seed: SeedOption = False) -> None:
    """Recompute the registry hash chain and report the first broken link."""
    path = seed_store().path if seed else store_path(get_settings())
    status = RegistryStore(path).verify()
    if not path.is_file():
        typer.echo(f"no registry at {path}")
        raise typer.Exit(2)
    if status.ok:
        legacy = f" ({status.legacy} unhashed legacy records)" if status.legacy else ""
        typer.echo(f"OK {status.records} records head={status.head_hash}{legacy} {path}")
        return
    typer.echo(f"BROKEN at line {status.broken_line}: {status.reason}; {path}")
    raise typer.Exit(1)
