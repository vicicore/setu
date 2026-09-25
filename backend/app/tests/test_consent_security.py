"""Phase 7 priority 6: a consent record must gate the connector exchange
it authorizes for its full lifecycle — active, revoked, and expired.
Grant->submit and revoke->blocked are already exercised end to end over
HTTP in test_journeys_api.py; expiry is proven here at the orchestrator
level because the HTTP API deliberately does not let a citizen choose
their own consent validity period (see grant_consent's validity_days
default in app/services/orchestrator.py), so there is no way to produce
an expired consent through the public API within a test's lifetime."""

from datetime import timedelta

import pytest

from app.repositories.local.connector_request_repository import LocalJsonConnectorRequestRepository
from app.services.connectors.revenue import RevenueMockConnector
from app.services.dependency_graph import COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH
from app.services.orchestrator import ConsentRequiredError, JourneyOrchestrator


@pytest.fixture
def orchestrator() -> JourneyOrchestrator:
    return JourneyOrchestrator()


def _journey(orchestrator: JourneyOrchestrator):
    return orchestrator.start_journey(
        citizen_id="citizen-consent-test",
        life_event_code="college_admission_scholarship",
        graph=COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH,
        already_verified_service_codes={"identity_verification", "domicile_certificate", "caste_certificate"},
    )


def test_active_consent_authorizes_the_connector_exchange(orchestrator: JourneyOrchestrator) -> None:
    journey = _journey(orchestrator)
    connector = RevenueMockConnector(LocalJsonConnectorRequestRepository())
    orchestrator.grant_consent(journey, "income_certificate", purpose="test")
    consent = journey.consents["income_certificate"]
    assert consent.is_active is True

    external_reference = orchestrator.submit_to_connector(
        journey, "income_certificate", connector, payload={}
    )
    assert external_reference.startswith("REV-")


def test_revoked_consent_blocks_the_connector_exchange(orchestrator: JourneyOrchestrator) -> None:
    journey = _journey(orchestrator)
    connector = RevenueMockConnector(LocalJsonConnectorRequestRepository())
    orchestrator.grant_consent(journey, "income_certificate", purpose="test")
    orchestrator.revoke_consent(journey, "income_certificate")
    assert journey.consents["income_certificate"].is_active is False

    with pytest.raises(ConsentRequiredError):
        orchestrator.submit_to_connector(journey, "income_certificate", connector, payload={})


def test_expired_consent_blocks_the_connector_exchange(orchestrator: JourneyOrchestrator) -> None:
    journey = _journey(orchestrator)
    connector = RevenueMockConnector(LocalJsonConnectorRequestRepository())
    # validity_days=-1 produces a consent whose expires_at is already in
    # the past — is_active checks expiry independently of revocation.
    orchestrator.grant_consent(journey, "income_certificate", purpose="test", validity_days=-1)
    consent = journey.consents["income_certificate"]
    assert consent.revoked_at is None  # not revoked...
    assert consent.is_active is False  # ...but expired, which must also block

    with pytest.raises(ConsentRequiredError):
        orchestrator.submit_to_connector(journey, "income_certificate", connector, payload={})


def test_consent_expiry_is_based_on_expires_at_not_a_separate_flag(
    orchestrator: JourneyOrchestrator,
) -> None:
    """Guards against a regression where is_active only checked
    revoked_at — expires_at must independently gate access."""
    journey = _journey(orchestrator)
    orchestrator.grant_consent(journey, "income_certificate", purpose="test", validity_days=30)
    consent = journey.consents["income_certificate"]
    assert consent.is_active is True

    consent.expires_at = consent.granted_at - timedelta(seconds=1)
    assert consent.is_active is False
