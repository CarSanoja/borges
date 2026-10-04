from __future__ import annotations

from starlette.requests import Request

from borges.config import Settings
from borges.identity.client_address import client_address


def request(peer: str | None, forwarded: str | None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    scope = {
        "type": "http",
        "headers": headers,
        "client": (peer, 1) if peer else None,
    }
    return Request(scope)


def test_forwarded_for_is_ignored_unless_a_proxy_is_trusted() -> None:
    settings = Settings(_env_file=None)
    assert client_address(request("10.0.0.1", "9.9.9.9"), settings) == "10.0.0.1"


def test_a_trusted_proxy_supplies_the_client_as_its_last_hop() -> None:
    settings = Settings(_env_file=None, borges_trusted_proxy=True)
    assert client_address(request("10.0.0.1", "6.6.6.6, 9.9.9.9"), settings) == "9.9.9.9"


def test_hops_pick_an_earlier_entry() -> None:
    settings = Settings(_env_file=None, borges_trusted_proxy=True, borges_trusted_proxy_hops=2)
    assert client_address(request("10.0.0.1", "6.6.6.6, 9.9.9.9"), settings) == "6.6.6.6"


def test_a_missing_or_malformed_header_falls_back_to_the_peer() -> None:
    settings = Settings(_env_file=None, borges_trusted_proxy=True)
    assert client_address(request("10.0.0.1", None), settings) == "10.0.0.1"
    assert client_address(request("10.0.0.1", "not-an-ip"), settings) == "10.0.0.1"
    assert client_address(request(None, None), settings) == "unknown"
