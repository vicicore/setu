"""Proves the College Admission + Scholarship signature demo (Master
Prompt section 5 / Build README section 4) is a real state machine, not
a scripted UI animation: every assertion reads back mutated Journey
state produced by the orchestrator + a mock connector."""

import pytest

from app.schemas.enums import ApplicationStepStatus
from app.services.connectors.revenue import RevenueMockConnector
from app.services.dependency_graph import COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH
from app.services.orchestrator import (
    ConsentRequiredError,
    DependencyNotMetError,
    JourneyOrchestrator,
)


@pytest.fixture
def orchestrator() -> JourneyOrchestrator:
    return JourneyOrchestrator()


def test_signature_demo_end_to_end(orchestrator: JourneyOrchestrator) -> None:
    # Seed state: identity, domicile and caste already verified for this
    # synthetic citizen; income certificate has not been obtained yet.
    journey = orchestrator.start_journey(
        citizen_id="citizen-demo-1",
        graph=COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH,
        already_verified_service_codes={
            "identity_verification",
            "domicile_certificate",
            "caste_certificate",
        },
    )

    # 1. Income certificate has no connector submission yet -> NOT_STARTED.
    assert journey.step("income_certificate").status == ApplicationStepStatus.NOT_STARTED

    # 2. Scholarship is blocked purely because income_certificate isn't
    #    verified yet — this is computed, not hardcoded.
    scholarship = journey.step("education_scholarship")
    assert scholarship.status == ApplicationStepStatus.BLOCKED
    assert "income_certificate" in scholarship.blocked_reason.lower().replace(" ", "_") \
        or "income certificate" in scholarship.blocked_reason.lower()

    # 3. Submitting to the Revenue connector without consent must fail —
    #    consent is not decorative.
    connector = RevenueMockConnector()
    with pytest.raises(ConsentRequiredError):
        orchestrator.submit_to_connector(
            journey, "income_certificate", connector, payload={"citizen_id": "citizen-demo-1"}
        )

    # 4. Grant consent, then submit — step must move to IN_PROGRESS with a
    #    real external reference from the connector.
    orchestrator.grant_consent(
        journey, "income_certificate", purpose="Verify income for scholarship eligibility"
    )
    external_reference = orchestrator.submit_to_connector(
        journey, "income_certificate", connector, payload={"citizen_id": "citizen-demo-1"}
    )
    assert external_reference.startswith("REV-")
    assert journey.step("income_certificate").status == ApplicationStepStatus.IN_PROGRESS

    # 5. Scholarship remains BLOCKED (staged, not failed) while income is
    #    in progress — matches "Scholarship remains staged, not failed."
    assert journey.step("education_scholarship").status == ApplicationStepStatus.BLOCKED

    # 6. Simulate the Revenue department approving the certificate, and
    #    the orchestrator receiving that as a webhook/n8n event.
    connector.simulate_approval(external_reference)
    changed = orchestrator.receive_connector_event(
        journey, "income_certificate", event_status="approved"
    )

    # 7. Income certificate is now VERIFIED, and — critically — the
    #    scholarship step was updated *automatically* as a cascade of
    #    that single event, with no direct call touching "scholarship".
    assert journey.step("income_certificate").status == ApplicationStepStatus.VERIFIED
    assert "education_scholarship" in changed
    assert journey.step("education_scholarship").status == ApplicationStepStatus.READY
    assert journey.step("education_scholarship").blocked_reason is None

    # 8. The whole journey is now resolvable end to end, and the unified
    #    timeline recorded every cross-department transition in order.
    assert journey.is_complete()
    assert any("submitted to Revenue" in event for event in journey.timeline)
    assert any("VERIFIED (department approval received)" in event for event in journey.timeline)
    assert any("education_scholarship -> ready" in event for event in journey.timeline)


def test_cannot_submit_before_dependency_is_verified(orchestrator: JourneyOrchestrator) -> None:
    journey = orchestrator.start_journey(
        citizen_id="citizen-demo-2",
        graph=COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH,
        already_verified_service_codes=set(),  # nothing verified yet
    )
    orchestrator.grant_consent(journey, "education_scholarship", purpose="test")
    connector = RevenueMockConnector()
    with pytest.raises(DependencyNotMetError):
        orchestrator.submit_to_connector(
            journey, "education_scholarship", connector, payload={}
        )


def test_rejection_blocks_dependents_with_reason(orchestrator: JourneyOrchestrator) -> None:
    journey = orchestrator.start_journey(
        citizen_id="citizen-demo-3",
        graph=COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH,
        already_verified_service_codes={"identity_verification", "domicile_certificate", "caste_certificate"},
    )
    connector = RevenueMockConnector()
    orchestrator.grant_consent(journey, "income_certificate", purpose="test")
    ref = orchestrator.submit_to_connector(journey, "income_certificate", connector, payload={})
    connector.simulate_rejection(ref, reason="Income proof insufficient")
    orchestrator.receive_connector_event(journey, "income_certificate", event_status="rejected")

    scholarship = journey.step("education_scholarship")
    assert scholarship.status == ApplicationStepStatus.BLOCKED
    assert "rejected" in scholarship.blocked_reason.lower()
