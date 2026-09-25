from pydantic import BaseModel

ALLOWED_STATUSES = {"approved", "rejected"}


class ConnectorWebhookPayload(BaseModel):
    """Matches the shape every GovernmentConnector.emit_webhook_event()
    produces (see app/services/connectors/base.py) — the same payload
    shape a real department system's n8n workflow would forward."""

    external_reference: str
    service_code: str
    status: str
    department: str


class WebhookAck(BaseModel):
    application_id: str | None
    service_code: str
    accepted_status: str
