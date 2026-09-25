from app.services.connectors.base import GovernmentConnector


class UrbanDevelopmentMockConnector(GovernmentConnector):
    department = "Urban Development"
    default_sla_days = 14

    def emit_webhook_event(self, external_reference: str) -> dict:
        record = self.get_status(external_reference)
        return {
            "event": "urban_development.noc.status_changed",
            "external_reference": record.external_reference,
            "service_code": record.service_code,
            "status": record.status,
            "department": self.department,
        }
