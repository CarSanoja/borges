from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Annotated

import typer

from borges.config import get_settings
from borges.identity.api_key import parse_duration
from borges.identity.chain import ChainBroken
from borges.identity.keystore import KeyRecord, KeyStoreError, open_keystore
from borges.identity.scopes import UnknownScope

keys_app = typer.Typer(
    name="keys", help="Create, list and revoke named API keys.", no_args_is_help=True
)


def _when(value: float | None) -> str:
    if value is None:
        return "never"
    return datetime.fromtimestamp(value, UTC).strftime("%Y-%m-%d %H:%M UTC")


def _row(record: KeyRecord, now: float) -> str:
    scopes = ",".join(sorted(record.scopes))
    return "\t".join(
        [
            record.key_id,
            record.name,
            record.status(now),
            scopes,
            f"created {_when(record.created_at)}",
            f"expires {_when(record.expires_at)}",
        ]
    )


def _fail(message: str, code: int = 1) -> typer.Exit:
    typer.echo(message, err=True)
    return typer.Exit(code)


@keys_app.command()
def create(
    name: Annotated[str, typer.Option("--name", help="Caller name, e.g. ci or alice")],
    scopes: Annotated[str, typer.Option("--scopes", help="Comma-separated scopes")],
    expires: Annotated[str, typer.Option("--expires", help="30d, 12h, 90m or never")] = "never",
) -> None:
    """Create a key; the secret is printed once and only its salted hash is stored."""
    store = open_keystore(get_settings())
    try:
        record, token = store.create(name, scopes, parse_duration(expires))
    except (KeyStoreError, UnknownScope, ValueError) as error:
        raise _fail(str(error), 2) from None
    except ChainBroken as broken:
        raise _fail(str(broken)) from None
    typer.echo(f"key_id {record.key_id}")
    typer.echo(f"principal {record.principal_id}")
    typer.echo(f"scopes {','.join(sorted(record.scopes))}")
    typer.echo(f"expires {_when(record.expires_at)}")
    typer.echo("this is the only time the key is shown:")
    typer.echo(token)


@keys_app.command("list")
def list_keys() -> None:
    """Show every key with its status, scopes and expiry (never the secret)."""
    try:
        records = open_keystore(get_settings()).listing()
    except ChainBroken as broken:
        raise _fail(str(broken)) from None
    now = time.time()
    for record in records:
        typer.echo(_row(record, now))
    if not records:
        typer.echo("no keys")


@keys_app.command()
def revoke(
    key_id: Annotated[str, typer.Argument(help="The key id shown by `borges keys list`")],
) -> None:
    """Revoke a key so it stops authenticating at once."""
    try:
        record = open_keystore(get_settings()).revoke(key_id)
    except KeyStoreError as error:
        raise _fail(str(error), 2) from None
    except ChainBroken as broken:
        raise _fail(str(broken)) from None
    typer.echo(f"revoked {record.key_id} ({record.name})")


@keys_app.command()
def verify() -> None:
    """Recompute the key store hash chain."""
    store = open_keystore(get_settings())
    status = store.verify()
    if status.ok:
        typer.echo(
            f"OK {status.records} records head={status.head_hash} {store.path} ({status.notice})"
        )
        return
    typer.echo(
        f"BROKEN at line {status.broken_line}: {status.reason}; {store.path} ({status.notice})"
    )
    raise typer.Exit(1)
