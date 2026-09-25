from datetime import date, datetime, timezone

from app.repositories.interfaces import CitizenRepository
from app.repositories.models import CitizenProfileRecord
from app.schemas.citizen import CitizenProfileUpdate


class CitizenProfileService:
    def __init__(self, citizen_repo: CitizenRepository) -> None:
        self._citizens = citizen_repo

    def get_profile(self, citizen_id: str) -> CitizenProfileRecord | None:
        return self._citizens.get(citizen_id)

    def upsert_profile(
        self, citizen_id: str, update: CitizenProfileUpdate
    ) -> CitizenProfileRecord:
        existing = self._citizens.get(citizen_id)
        now = datetime.now(timezone.utc)

        def _as_str(value: date | None) -> str | None:
            return value.isoformat() if value else None

        merged = CitizenProfileRecord(
            citizen_id=citizen_id,
            full_name=update.full_name or (existing.full_name if existing else ""),
            dob=_as_str(update.dob) or (existing.dob if existing else None),
            district=update.district or (existing.district if existing else None),
            taluka=update.taluka or (existing.taluka if existing else None),
            phone=update.phone or (existing.phone if existing else None),
            email=existing.email if existing else None,
            preferred_language=update.preferred_language
            or (existing.preferred_language if existing else "en"),
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        return self._citizens.upsert(merged)

    def profile_completeness_pct(self, record: CitizenProfileRecord) -> int:
        fields = [record.full_name, record.dob, record.district, record.taluka, record.phone]
        filled = sum(1 for f in fields if f)
        return round(100 * filled / len(fields))
