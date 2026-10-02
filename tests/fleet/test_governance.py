from __future__ import annotations

import pytest

from borges.config import Settings
from borges.fleet.fleet import Fleet
from borges.fleet.governance import change_state, publish_audited
from borges.fleet.store import RegistryStore, TransitionError
from borges.telemetry.audit_verify import verify_chain
from borges.telemetry.run_telemetry import global_audit_path


def test_publish_and_approve_are_audited(
    settings: Settings, fleet: Fleet, empty_store: RegistryStore
) -> None:
    publish_audited(empty_store, fleet, settings, "alice")
    change_state(empty_store, "judge", "1.0.0", "approved", settings, "bob", "reviewed")
    path = global_audit_path(settings)
    assert verify_chain(path).ok
    kinds = [line for line in path.read_text().splitlines()]
    assert sum('"registry.publish"' in line for line in kinds) == len(fleet.agents)
    assert any('"registry.approval"' in line and '"bob"' in line for line in kinds)


def test_retire_after_approve_and_no_return(fleet: Fleet, empty_store: RegistryStore) -> None:
    publish_audited(empty_store, fleet)
    change_state(empty_store, "judge", "1.0.0", "approved")
    assert change_state(empty_store, "judge", "1.0.0", "retired").state == "retired"
    with pytest.raises(TransitionError):
        change_state(empty_store, "judge", "1.0.0", "approved")
