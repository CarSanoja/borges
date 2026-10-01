from __future__ import annotations

import os

import pytest

from borges.config import Settings
from borges.llm.client import Role
from borges.llm.nebius_provider import NebiusLLM

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("NEBIUS_API_KEY") or os.environ.get("BORGES_LIVE_TESTS") != "1",
        reason="needs NEBIUS_API_KEY and BORGES_LIVE_TESTS=1",
    ),
]


async def test_coder_role_answers() -> None:
    settings = Settings()
    llm = NebiusLLM(api_key=os.environ["NEBIUS_API_KEY"], base_url=settings.nebius_base_url)
    response = await llm.complete(
        Role.CODER, [{"role": "user", "content": "Say hi."}], key="live:coder", max_tokens=32
    )
    assert response.usage.tokens_out > 0
    assert response.usage.cost_usd > 0
