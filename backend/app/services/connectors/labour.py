from app.services.connectors.base import GovernmentConnector


class LabourMockConnector(GovernmentConnector):
    department = "Labour"
    default_sla_days = 10

    def emit_webhook_event(self, external_reference: str) -> dict:
        record = self.get_status(external_reference)
        return {
            "event": "labour.registration.status_changed",
            "external_reference": record.external_reference,
            "service_code": record.service_code,
            "status": record.status,
            "department": self.department,
        }
