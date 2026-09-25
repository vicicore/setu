from datetime import datetime, timezone

from app.schemas.enums import SlaStatus

AT_RISK_THRESHOLD = 0.2  # last 20% of the SLA window counts as "at risk"


def compute_sla_status(
    due_at: datetime | None, submitted_at: datetime | None, now: datetime | None = None
) -> SlaStatus | None:
    if due_at is None or submitted_at is None:
        return None
    now = now or datetime.now(timezone.utc)
    total_window = (due_at - submitted_at).total_seconds()
    if total_window <= 0:
        return SlaStatus.BREACHED if now >= due_at else SlaStatus.AT_RISK
    remaining = (due_at - now).total_seconds()
    if remaining <= 0:
        return SlaStatus.BREACHED
    if remaining / total_window <= AT_RISK_THRESHOLD:
        return SlaStatus.AT_RISK
    return SlaStatus.ON_TRACK
