from fastapi import APIRouter, Depends

from app.core.container import get_application_repository
from app.core.security import get_current_session, require_admin
from app.repositories.models import SessionRecord
from app.schemas.admin import AdminMetrics
from app.services.admin_metrics import compute_metrics

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics", response_model=AdminMetrics)
def get_admin_metrics(session: SessionRecord = Depends(get_current_session)) -> AdminMetrics:
    require_admin(session)
    applications = get_application_repository().list_all()
    return compute_metrics(applications)
