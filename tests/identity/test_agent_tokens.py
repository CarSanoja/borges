from __future__ import annotations

import pytest

from borges.identity.agent_tokens import AgentTokenInvalid, AgentTokenIssuer, process_issuer

PRINCIPAL = "agent://borges/planner"
CAPS = ["spend.use", "dataset.profile.read"]


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def issuer(clock: Clock) -> AgentTokenIssuer:
    return AgentTokenIssuer(secret=b"s" * 32, clock=clock)


def test_valid_token_carries_its_claims(issuer: AgentTokenIssuer) -> None:
    claims = issuer.verify(issuer.mint("r1", PRINCIPAL, CAPS, 60), run_id="r1")
    assert claims.run_id == "r1" and claims.principal == PRINCIPAL
    assert claims.capabilities == set(CAPS)
    assert claims.expires_at == 1060.0


def test_forged_signature_is_rejected(issuer: AgentTokenIssuer) -> None:
    payload, _, _ = issuer.mint("r1", PRINCIPAL, CAPS, 60).partition(".")
    with pytest.raises(AgentTokenInvalid) as caught:
        issuer.verify(f"{payload}.{'0' * 64}")
    assert caught.value.failure == "bad_signature"


def test_tampered_payload_is_rejected(issuer: AgentTokenIssuer) -> None:
    other = issuer.mint("r1", "agent://borges/judge", ["llm.invoke:x"], 60)
    signature = issuer.mint("r1", PRINCIPAL, CAPS, 60).split(".")[1]
    with pytest.raises(AgentTokenInvalid) as caught:
        issuer.verify(f"{other.split('.')[0]}.{signature}")
    assert caught.value.failure == "bad_signature"


def test_token_from_another_process_secret_is_rejected(issuer: AgentTokenIssuer) -> None:
    foreign = AgentTokenIssuer(secret=b"x" * 32).mint("r1", PRINCIPAL, CAPS, 60)
    with pytest.raises(AgentTokenInvalid) as caught:
        issuer.verify(foreign)
    assert caught.value.failure == "bad_signature"


def test_expired_token_is_rejected(issuer: AgentTokenIssuer, clock: Clock) -> None:
    token = issuer.mint("r1", PRINCIPAL, CAPS, 60)
    clock.now += 61
    with pytest.raises(AgentTokenInvalid) as caught:
        issuer.verify(token)
    assert caught.value.failure == "expired"


def test_wrong_run_is_rejected(issuer: AgentTokenIssuer) -> None:
    token = issuer.mint("r1", PRINCIPAL, CAPS, 60)
    with pytest.raises(AgentTokenInvalid) as caught:
        issuer.verify(token, run_id="r2")
    assert caught.value.failure == "wrong_run"


def test_wrong_agent_is_rejected(issuer: AgentTokenIssuer) -> None:
    token = issuer.mint("r1", PRINCIPAL, CAPS, 60)
    with pytest.raises(AgentTokenInvalid) as caught:
        issuer.verify(token, principal="agent://borges/judge")
    assert caught.value.failure == "wrong_agent"


@pytest.mark.parametrize("junk", ["", "abc", ".", "a.", ".b", "é.é"])
def test_malformed_tokens_are_rejected(issuer: AgentTokenIssuer, junk: str) -> None:
    with pytest.raises(AgentTokenInvalid):
        issuer.verify(junk)


def test_process_issuer_is_stable_within_a_process() -> None:
    assert process_issuer() is process_issuer()
