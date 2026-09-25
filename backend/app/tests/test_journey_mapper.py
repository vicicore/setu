"""Proves domain Journey -> ApplicationRecord -> domain Journey is
lossless for everything the orchestrator relies on (status, consent,
SLA fields, timeline) — the seam that lets JourneyOrchestrator stay
storage-agnostic while a repository still persists its full state."""

from app.repositories.local.connector_request_repository import LocalJsonConnectorRequestRepository
from app.services.connectors.revenue import RevenueMockConnector
from app.services.dependency_graph import COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH
from app.services.journey_mapper import to_domain, to_record
from app.services.orchestrator import JourneyOrchestrator


def test_round_trip_preserves_state_through_a_full_scenario() -> None:
    orchestrator = JourneyOrchestrator()
    journey = orchestrator.start_journey(
        citizen_id="citizen-mapper-test",
        life_event_code="college_admission_scholarship",
        graph=COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH,
        already_verified_service_codes={"identity_verification", "domicile_certificate", "caste_certificate"},
    )
    orchestrator.grant_consent(journey, "income_certificate", purpose="test purpose")
    connector = RevenueMockConnector(LocalJsonConnectorRequestRepository())
    ref = orchestrator.submit_to_connector(journey, "income_certificate", connector, payload={})
    connector.simulate_approval(ref)
    orchestrator.receive_connector_event(journey, "income_certificate", event_status="approved")

    record = to_record(journey)
    restored = to_domain(record)

    assert restored.id == journey.id
    assert restored.life_event_code == journey.life_event_code
    assert restored.timeline == journey.timeline
    for code in journey.steps:
        assert restored.steps[code].status == journey.steps[code].status
        assert restored.steps[code].external_reference == journey.steps[code].external_reference
        assert restored.steps[code].sla_due_at == journey.steps[code].sla_due_at
    assert restored.consents["income_certificate"].is_active == journey.consents["income_certificate"].is_active
    # The reconstructed graph must be functionally identical — a
    # downstream orchestrator call on the restored Journey must behave
    # the same as on the original.
    assert restored.is_complete() == journey.is_complete()
