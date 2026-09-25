from app.services.connectors.base import GovernmentConnector


class HomeAffairsMockConnector(GovernmentConnector):
    """Backs identity_verification (Aadhaar/DigiLocker-style checks),
    department="Home" in the catalog. Added after live testing showed
    every citizen without a vault-pre-verified identity (i.e. anyone
    outside the /demo seeding) hit "No connector registered for
    department 'Home'" the moment they tried to submit it — the college
    admission demo never exercised this path because its citizen always
    started with identity already verified."""

    department = "Home"
    default_sla_days = 1

    def emit_webhook_event(self, external_reference: str) -> dict:
        record = self.get_status(external_reference)
        return {
            "event": "home.identity_verification.status_changed",
            "external_reference": record.external_reference,
            "service_code": record.service_code,
            "status": record.status,
            "department": self.department,
        }
