from fastapi import APIRouter, HTTPException

from app.schemas.life_event import LifeEventDetail, LifeEventService, LifeEventSummary
from app.services.dependency_graph import get_graph
from app.services.life_event_catalog import get_life_event_meta, list_life_event_codes

router = APIRouter(prefix="/life-events", tags=["life-events"])


@router.get("", response_model=list[LifeEventSummary])
def list_life_events() -> list[LifeEventSummary]:
    return [
        LifeEventSummary(
            code=meta.code,
            title_en=meta.title_en,
            title_mr=meta.title_mr,
            description_en=meta.description_en,
            description_mr=meta.description_mr,
        )
        for meta in (get_life_event_meta(code) for code in list_life_event_codes())
    ]


@router.get("/{code}", response_model=LifeEventDetail)
def get_life_event(code: str) -> LifeEventDetail:
    try:
        meta = get_life_event_meta(code)
        graph = get_graph(code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return LifeEventDetail(
        code=meta.code,
        title_en=meta.title_en,
        title_mr=meta.title_mr,
        description_en=meta.description_en,
        description_mr=meta.description_mr,
        goal_statement_en=meta.goal_statement_en,
        goal_statement_mr=meta.goal_statement_mr,
        services=[
            LifeEventService(
                service_code=s,
                display_name=graph.display_name_of(s),
                department=graph.department_of(s),
                requires_service_codes=graph.requirements_of(s),
            )
            for s in graph.service_codes
        ],
    )
