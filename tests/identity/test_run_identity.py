from __future__ import annotations

from borges.config import Settings
from borges.identity.agent_tokens import AgentTokenIssuer
from borges.identity.run_identity import mint_run_identity


def test_every_roster_agent_gets_a_run_bound_token(settings: Settings) -> None:
    issuer = AgentTokenIssuer(secret=b"k" * 32)
    identity = mint_run_identity(settings, "run-1", issuer)
    assert {"planner", "coder", "judge", "harness"} <= set(identity.tokens)
    claims = issuer.verify(identity.token_for("planner") or "", run_id="run-1")
    assert claims.principal == "agent://borges/planner"
    assert "spend.use" in claims.capabilities
    assert identity.token_for("ghost") is None


def test_tokens_expire_after_the_configured_ttl(tmp_path) -> None:
    settings = Settings(_env_file=None, borges_home=tmp_path, borges_agent_token_ttl_s=90)
    now = [10.0]
    issuer = AgentTokenIssuer(secret=b"k" * 32, clock=lambda: now[0])
    identity = mint_run_identity(settings, "r", issuer)
    assert identity.expires_at == 100.0
