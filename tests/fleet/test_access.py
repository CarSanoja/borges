from __future__ import annotations

from borges.config import Settings
from borges.fleet.access import allows, capabilities_of


def test_capabilities_are_read_from_the_registry(settings: Settings) -> None:
    granted = capabilities_of(settings, "agent://borges/harness")
    assert granted == {"sandbox.exec", "dataset.rows.read"}
    assert capabilities_of(settings, "agent://borges/ghost") == frozenset()
    assert capabilities_of(settings, "user:alice") == frozenset()


def test_allows_checks_one_capability(settings: Settings) -> None:
    assert allows(settings, "agent://borges/judge", "spend.use")
    assert not allows(settings, "agent://borges/judge", "sandbox.exec")
