from __future__ import annotations

from borges.config import Settings
from borges.identity.run_quota import active_limit
from borges.runtime.jobs import Job
from borges.runtime.queue import Admit


def make_admit(settings: Settings) -> Admit:
    """Claim-time caps: total active runs, live runs and the owner's own active runs."""

    def admit(job: Job, running: list[Job]) -> bool:
        if len(running) >= settings.borges_max_active_runs:
            return False
        if job.live and sum(1 for r in running if r.live) >= settings.borges_max_live_runs:
            return False
        owned = sum(1 for r in running if r.owner_key == job.owner_key)
        return owned < active_limit(settings, job.anonymous)

    return admit
