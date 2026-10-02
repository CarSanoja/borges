from __future__ import annotations

from borges.config import Settings
from borges.identity.authentication import Authenticator
from borges.identity.keystore import open_keystore
from borges.identity.principal import ANONYMOUS, LEGACY


def test_no_credentials_is_anonymous(settings: Settings) -> None:
    result = Authenticator(settings).authenticate({})
    assert result.principal == ANONYMOUS and result.failure is None


def test_valid_bearer_resolves_the_named_principal(settings: Settings) -> None:
    _, token = open_keystore(settings).create("ci", "audit:read")
    result = Authenticator(settings).authenticate({"authorization": f"Bearer {token}"})
    assert result.principal.id == "caller://ci"


def test_bad_bearer_is_a_failure_not_a_downgrade(settings: Settings) -> None:
    result = Authenticator(settings).authenticate({"authorization": "Bearer bk_x_y"})
    assert result.failure == "unknown_key"
    assert Authenticator(settings).authenticate({"authorization": "Basic abc"}).failure


def test_legacy_header_needs_the_configured_token(tmp_path) -> None:
    configured = Settings(_env_file=None, borges_home=tmp_path, borges_live_token="s3cret")
    auth = Authenticator(configured)
    assert auth.authenticate({"x-borges-live-token": "s3cret"}).principal == LEGACY
    assert auth.authenticate({"x-borges-live-token": "nope"}).principal == ANONYMOUS
    plain = Authenticator(Settings(_env_file=None, borges_home=tmp_path))
    assert plain.authenticate({"x-borges-live-token": "s3cret"}).principal == ANONYMOUS
