from fastapi import APIRouter

from app.core.container import get_application_repository
from app.schemas.admin import AdminMetrics
from app.services.admin_metrics import compute_metrics

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics", response_model=AdminMetrics)
def get_admin_metrics() -> AdminMetrics:
    applications = get_application_repository().list_all()
    return compute_metrics(applications)
