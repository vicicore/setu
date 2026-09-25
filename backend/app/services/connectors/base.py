import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.repositories.interfaces import ConnectorRequestRepository
from app.repositories.models import ConnectorRequestRecord


@dataclass
class ConnectorResponse:
    external_reference: str
    department: str
    status: str
    timestamp: datetime
    sla_deadline: datetime
    next_action: str


class GovernmentConnector(ABC):
    """Common contract every department connector (mock or, later, real)
    must satisfy. See Master Prompt section 12 — this interface is what
    lets a mock connector be swapped for a real government API without
    touching the orchestrator.

    Request bookkeeping is persisted through a ConnectorRequestRepository
    rather than kept in a Python-process dict — a backend restart between
    submit() and simulate_approval()/simulate_rejection() must not lose
    it (Phase 7 priority 5)."""

    department: str
    default_sla_days: int = 7
    simulated_latency_seconds: float = 0.0

    def __init__(self, repository: ConnectorRequestRepository) -> None:
        self._repository = repository

    def submit(self, service_code: str, payload: dict) -> ConnectorResponse:
        if self.simulated_latency_seconds:
            time.sleep(self.simulated_latency_seconds)
        reference = f"{self.department[:3].upper()}-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=self.default_sla_days)
        record = ConnectorRequestRecord(
            external_reference=reference,
            department=self.department,
            service_code=service_code,
            status="submitted",
            submitted_at=now,
            sla_deadline=deadline,
            payload=payload,
        )
        self._repository.save(record)
        return ConnectorResponse(
            external_reference=reference,
            department=self.department,
            status=record.status,
            timestamp=now,
            sla_deadline=deadline,
            next_action="await_department_review",
        )

    def get_status(self, external_reference: str) -> ConnectorRequestRecord:
        record = self._repository.get(external_reference)
        if record is None:
            raise KeyError(f"No connector request found for {external_reference!r}")
        return record

    def simulate_approval(self, external_reference: str) -> ConnectorRequestRecord:
        record = self.get_status(external_reference)
        record.status = "approved"
        self._repository.save(record)
        return record

    def simulate_rejection(self, external_reference: str, reason: str = "") -> ConnectorRequestRecord:
        record = self.get_status(external_reference)
        record.status = "rejected"
        record.payload["rejection_reason"] = reason
        self._repository.save(record)
        return record

    @abstractmethod
    def emit_webhook_event(self, external_reference: str) -> dict:
        """Return the payload this connector would POST to
        /webhooks/n8n/{event} for its current status."""
        raise NotImplementedError
