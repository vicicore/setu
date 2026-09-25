from fastapi import APIRouter, HTTPException

from app.core.container import get_citizen_profile_service
from app.schemas.citizen import CitizenProfileUpdate, CitizenProfileView

router = APIRouter(prefix="/citizens", tags=["citizens"])


@router.get("/{citizen_id}/profile", response_model=CitizenProfileView)
def get_profile(citizen_id: str) -> CitizenProfileView:
    service = get_citizen_profile_service()
    record = service.get_profile(citizen_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Citizen profile not found")
    return CitizenProfileView(
        **record.model_dump(),
        profile_completeness_pct=service.profile_completeness_pct(record),
    )


@router.put("/{citizen_id}/profile", response_model=CitizenProfileView)
def upsert_profile(citizen_id: str, update: CitizenProfileUpdate) -> CitizenProfileView:
    service = get_citizen_profile_service()
    record = service.upsert_profile(citizen_id, update)
    return CitizenProfileView(
        **record.model_dump(),
        profile_completeness_pct=service.profile_completeness_pct(record),
    )
