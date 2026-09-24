"""In-memory demo-mode state for the College Admission + Scholarship
signature journey. Deliberately independent of Supabase/Appwrite so the
`/demo` experience (Master Prompt section 9, Build README section 11)
runs on a clean machine with zero external accounts — judges should
never need cloud credentials to see the orchestration work.

This is NOT how citizen-real data is stored (that's Supabase, see
app/db/migrations/0001_init.sql) — it is a self-contained sandbox that
exercises the exact same JourneyOrchestrator used in production code."""

from app.services.connectors.revenue import RevenueMockConnector
from app.services.dependency_graph import COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH
from app.services.orchestrator import Journey, JourneyOrchestrator

DEMO_CITIZEN_ID = "demo-citizen-priya-deshmukh"
ALREADY_VERIFIED = {"identity_verification", "domicile_certificate", "caste_certificate"}


class DemoSession:
    def __init__(self) -> None:
        self.orchestrator = JourneyOrchestrator()
        self.revenue_connector = RevenueMockConnector()
        self.journey: Journey = self._new_journey()

    def _new_journey(self) -> Journey:
        return self.orchestrator.start_journey(
            citizen_id=DEMO_CITIZEN_ID,
            graph=COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH,
            already_verified_service_codes=set(ALREADY_VERIFIED),
        )

    def reset(self) -> None:
        self.revenue_connector = RevenueMockConnector()
        self.journey = self._new_journey()

    def grant_consent(self) -> None:
        self.orchestrator.grant_consent(
            self.journey,
            "income_certificate",
            purpose="Verify family income for engineering scholarship eligibility",
        )

    def submit_income_certificate(self) -> str:
        return self.orchestrator.submit_to_connector(
            self.journey,
            "income_certificate",
            self.revenue_connector,
            payload={"citizen_id": DEMO_CITIZEN_ID, "declared_income_inr": 185000},
        )

    def approve_income_certificate(self) -> list[str]:
        step = self.journey.step("income_certificate")
        if step.external_reference is None:
            raise ValueError("Income certificate has not been submitted yet")
        self.revenue_connector.simulate_approval(step.external_reference)
        return self.orchestrator.receive_connector_event(
            self.journey, "income_certificate", event_status="approved"
        )


_demo_session: DemoSession | None = None


def get_demo_session() -> DemoSession:
    global _demo_session
    if _demo_session is None:
        _demo_session = DemoSession()
    return _demo_session
