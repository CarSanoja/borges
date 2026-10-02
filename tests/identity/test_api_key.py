from __future__ import annotations

import pytest

from borges.identity import api_key


def test_token_roundtrip_even_when_the_secret_has_underscores() -> None:
    token = api_key.format_token("abc123", "se_cr-et_")
    assert token.startswith("bk_")
    assert api_key.parse_token(token) == ("abc123", "se_cr-et_")


@pytest.mark.parametrize("bad", ["", "bk_", "bk_onlyid", "xx_a_b", "bk__secret"])
def test_malformed_tokens_do_not_parse(bad: str) -> None:
    assert api_key.parse_token(bad) is None


def test_hash_is_salted_and_checked_in_constant_time() -> None:
    salt_a, salt_b = api_key.new_salt(), api_key.new_salt()
    digest = api_key.hash_secret(salt_a, "s")
    assert digest != api_key.hash_secret(salt_b, "s")
    assert api_key.secret_matches(salt_a, digest, "s")
    assert not api_key.secret_matches(salt_a, digest, "t")


@pytest.mark.parametrize(
    ("raw", "seconds"), [("30d", 2592000.0), ("12h", 43200.0), ("90m", 5400.0), ("1w", 604800.0)]
)
def test_durations(raw: str, seconds: float) -> None:
    assert api_key.parse_duration(raw) == seconds


def test_never_means_no_expiry_and_garbage_is_an_error() -> None:
    assert api_key.parse_duration("never") is None
    with pytest.raises(ValueError, match="duration"):
        api_key.parse_duration("soon")


def test_names_are_restricted_to_safe_identifiers() -> None:
    assert api_key.valid_name("ci-bot.1")
    assert not api_key.valid_name("Bad Name")
    assert not api_key.valid_name("a/b")
