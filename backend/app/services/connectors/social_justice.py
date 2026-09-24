from app.services.connectors.base import GovernmentConnector


class SocialJusticeMockConnector(GovernmentConnector):
    department = "Social Justice"
    default_sla_days = 15

    def emit_webhook_event(self, external_reference: str) -> dict:
        record = self.get_status(external_reference)
        return {
            "event": "social_justice.certificate.status_changed",
            "external_reference": record.external_reference,
            "service_code": record.service_code,
            "status": record.status,
            "department": self.department,
        }
