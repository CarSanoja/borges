"""Check the Nebius key, the three model ids and one structured call per role."""

from __future__ import annotations

import asyncio
import sys

import openai

from borges.config import Settings
from borges.llm.live_smoke import SMOKE_CAP_USD, render_report, run_smoke

NO_KEY = "NEBIUS_API_KEY is not set: put it in .env (never commit it) and run `make live-smoke`."


def main() -> int:
    settings = Settings()
    if not settings.nebius_api_key:
        print(NO_KEY, file=sys.stderr)
        return 2
    client = openai.AsyncOpenAI(
        base_url=settings.nebius_base_url,
        api_key=settings.nebius_api_key,
        timeout=60,
        max_retries=1,
    )
    report = asyncio.run(run_smoke(client, cap_usd=SMOKE_CAP_USD))
    print("\n".join(render_report(report)))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
