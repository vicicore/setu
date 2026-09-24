from app.services.connectors.base import GovernmentConnector


class EducationMockConnector(GovernmentConnector):
    department = "Higher Education"
    default_sla_days = 21

    def emit_webhook_event(self, external_reference: str) -> dict:
        record = self.get_status(external_reference)
        return {
            "event": "education.scholarship.status_changed",
            "external_reference": record.external_reference,
            "service_code": record.service_code,
            "status": record.status,
            "department": self.department,
        }
