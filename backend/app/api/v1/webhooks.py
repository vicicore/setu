from fastapi import APIRouter, Header, HTTPException

from app.core.config import get_settings
from app.core.container import get_journey_service
from app.schemas.webhook import ALLOWED_STATUSES, ConnectorWebhookPayload, WebhookAck

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_signature(provided_secret: str | None) -> None:
    configured_secret = get_settings().n8n_webhook_secret
    if configured_secret and provided_secret != configured_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


@router.post("/n8n/{event}", response_model=WebhookAck)
def receive_n8n_event(
    event: str,
    payload: ConnectorWebhookPayload,
    x_setu_webhook_secret: str | None = Header(default=None),
) -> WebhookAck:
    """Generic boundary for n8n (or any real department connector) to
    report a status change. `event` is the workflow/event label used for
    audit context only — routing to the right application happens via
    `payload.external_reference`, which is what a connector actually
    hands the department system. This calls the exact same
    JourneyService.receive_connector_event the /demo approve action
    uses; there is no separate webhook-specific orchestration path."""
    _verify_signature(x_setu_webhook_secret)

    if payload.status not in ALLOWED_STATUSES:
        # In-flight statuses (e.g. "submitted") are acknowledged but
        # don't drive a state transition — only a terminal outcome does.
        return WebhookAck(application_id=None, service_code=payload.service_code, accepted_status="ignored")

    try:
        journey = get_journey_service().receive_external_event(
            payload.external_reference, event_status=payload.status, source_event=event
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return WebhookAck(
        application_id=journey.id, service_code=payload.service_code, accepted_status=payload.status
    )
