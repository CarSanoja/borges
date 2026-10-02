from __future__ import annotations

import pytest

from borges.config import Settings
from borges.fleet.fleet import Fleet
from borges.fleet.governance import FourEyesViolation, change_state, publish_audited
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


def four_eyes(settings: Settings) -> Settings:
    return settings.model_copy(update={"borges_registry_four_eyes": True})


def test_publisher_cannot_approve_their_own_version_under_four_eyes(
    settings: Settings, fleet: Fleet, empty_store: RegistryStore
) -> None:
    strict = four_eyes(settings)
    publish_audited(empty_store, fleet, strict, "caller://alice")
    with pytest.raises(FourEyesViolation, match="cannot approve"):
        change_state(empty_store, "judge", "1.0.0", "approved", strict, "caller://alice")
    assert empty_store.get("judge", "1.0.0").state == "proposed"
    denied = [
        line for line in global_audit_path(strict).read_text().splitlines() if '"deny"' in line
    ]
    assert denied and "caller://alice" in denied[0]


def test_a_different_principal_can_approve_under_four_eyes(
    settings: Settings, fleet: Fleet, empty_store: RegistryStore
) -> None:
    strict = four_eyes(settings)
    publish_audited(empty_store, fleet, strict, "caller://alice")
    record = change_state(empty_store, "judge", "1.0.0", "approved", strict, "caller://bob")
    assert record.state == "approved"
    assert record.history[-1].by == "caller://bob"


def test_self_approval_is_allowed_when_four_eyes_is_off(
    settings: Settings, fleet: Fleet, empty_store: RegistryStore
) -> None:
    publish_audited(empty_store, fleet, settings, "caller://alice")
    change_state(empty_store, "judge", "1.0.0", "approved", settings, "caller://alice")
    assert empty_store.get("judge", "1.0.0").state == "approved"


def test_retiring_your_own_version_is_not_blocked(
    settings: Settings, fleet: Fleet, empty_store: RegistryStore
) -> None:
    strict = four_eyes(settings)
    publish_audited(empty_store, fleet, strict, "caller://alice")
    change_state(empty_store, "judge", "1.0.0", "retired", strict, "caller://alice")
