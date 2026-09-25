"""Proves Phase 7 priority 5: application state AND connector request
state survive a backend restart. Clearing every container lru_cache
mid-test simulates a fresh process starting up against the same
on-disk data directory — a legitimate way to test this without actually
spawning a new OS process, since the factories are the only place
process-lifetime state (the connector singletons) used to live."""

from fastapi.testclient import TestClient

from app.core import container

from app.main import app
from app.tests.conftest import login

client = TestClient(app)


def _restart_backend() -> None:
    """Simulates the backend process restarting: every cached singleton
    is dropped, so the next call to any container factory constructs a
    brand new instance — the only way state can survive is if it was
    actually written to the on-disk repository, not held in memory."""
    container.get_application_repository.cache_clear()
    container.get_audit_log_repository.cache_clear()
    container.get_journey_service.cache_clear()
    container.get_connector_request_repository.cache_clear()
    container.get_revenue_connector.cache_clear()
    container.get_auth_repository.cache_clear()
    container.get_auth_service.cache_clear()
    container._connector_registry.cache_clear()


def test_application_and_connector_state_survive_a_simulated_restart() -> None:
    citizen_id, headers = login(client)
    started = client.post(
        f"/api/v1/citizens/{citizen_id}/journeys",
        json={"life_event_code": "start_small_business"},
        headers=headers,
    ).json()
    application_id = started["application_id"]

    client.post(
        f"/api/v1/journeys/{application_id}/consent/business_registration",
        json={"purpose": "test"},
        headers=headers,
    )
    submitted = client.post(
        f"/api/v1/journeys/{application_id}/submit/business_registration", json={}, headers=headers
    ).json()
    step = next(s for s in submitted["steps"] if s["service_code"] == "business_registration")
    assert step["status"] == "in_progress"
    external_reference = step["external_reference"]

    # --- restart ---
    _restart_backend()

    # The session token itself must still resolve post-restart too — it
    # lives in the same repository abstraction as everything else.
    reread = client.get(f"/api/v1/journeys/{application_id}", headers=headers).json()
    reread_step = next(
        s for s in reread["steps"] if s["service_code"] == "business_registration"
    )
    assert reread_step["status"] == "in_progress"
    assert reread_step["external_reference"] == external_reference
    assert len(reread["timeline"]) == len(started["timeline"]) + 2  # consent + submit events

    # The connector's own bookkeeping for that reference must also still
    # exist post-restart — this is exactly what broke before Phase 7:
    # simulate_approval would KeyError on a fresh, empty in-memory dict.
    approved = client.post(
        f"/api/v1/journeys/{application_id}/approve/business_registration", headers=headers
    )
    assert approved.status_code == 200
    approved_step = next(
        s for s in approved.json()["steps"] if s["service_code"] == "business_registration"
    )
    assert approved_step["status"] == "verified"

    # Dependency resolution still works correctly after the restart too.
    assert next(
        s for s in approved.json()["steps"] if s["service_code"] == "local_noc"
    )["status"] == "ready"


def test_connector_request_repository_persists_across_fresh_instances(tmp_path) -> None:
    from app.repositories.local.connector_request_repository import (
        LocalJsonConnectorRequestRepository,
    )
    from app.repositories.models import ConnectorRequestRecord
    from datetime import datetime, timezone

    data_dir = str(tmp_path)
    repo = LocalJsonConnectorRequestRepository(data_dir=data_dir)
    now = datetime.now(timezone.utc)
    record = ConnectorRequestRecord(
        external_reference="TEST-abc123",
        department="Revenue",
        service_code="income_certificate",
        status="submitted",
        submitted_at=now,
        sla_deadline=now,
    )
    repo.save(record)

    fresh_repo = LocalJsonConnectorRequestRepository(data_dir=data_dir)
    reloaded = fresh_repo.get("TEST-abc123")
    assert reloaded is not None
    assert reloaded.status == "submitted"
    assert reloaded.department == "Revenue"
