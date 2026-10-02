from __future__ import annotations

import pytest

from borges.config import Settings
from borges.identity.run_scopes import scope_for_run
from borges.runs.models import RunRequest


@pytest.mark.parametrize(
    ("request_fields", "default_llm", "expected"),
    [
        ({"case_id": "a", "llm": "scripted"}, "scripted", "runs:create:scripted"),
        ({"case_id": "a", "llm": "nebius"}, "scripted", "runs:create:live:curated"),
        ({"case_id": "a"}, "nebius", "runs:create:live:curated"),
        ({"case_id": "a"}, "scripted", "runs:create:scripted"),
        ({"upload_id": "u" * 32, "llm": "scripted"}, "scripted", "runs:create:live:upload"),
        ({"upload_id": "u" * 32, "llm": "nebius"}, "scripted", "runs:create:live:upload"),
    ],
)
def test_scope_follows_the_request_mode(request_fields, default_llm, expected) -> None:
    settings = Settings(_env_file=None, borges_llm=default_llm)
    assert scope_for_run(RunRequest(**request_fields), settings) == expected
