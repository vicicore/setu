"""Citizen-facing metadata for each life event — titles/descriptions in
English and Marathi. Keyed by the same codes as
app/services/dependency_graph.GRAPH_REGISTRY and the `life_events` table
seeded in 0002_seed_catalog.sql, so a life_event_code is always resolved
against one definition, never duplicated as a frontend constant."""

from dataclasses import dataclass

from app.services.dependency_graph import get_graph


@dataclass(frozen=True)
class LifeEventMeta:
    code: str
    title_en: str
    title_mr: str
    description_en: str
    description_mr: str
    goal_statement_en: str
    goal_statement_mr: str


LIFE_EVENT_CATALOG: dict[str, LifeEventMeta] = {
    "college_admission_scholarship": LifeEventMeta(
        code="college_admission_scholarship",
        title_en="College Admission + Scholarship",
        title_mr="महाविद्यालय प्रवेश + शिष्यवृत्ती",
        description_en=(
            "Apply for an engineering admission scholarship — SETU checks your verified "
            "documents, requests consent, and coordinates Revenue and Higher Education for you."
        ),
        description_mr=(
            "अभियांत्रिकी प्रवेशासाठी शिष्यवृत्तीसाठी अर्ज करा — SETU तुमची पडताळणी केलेली कागदपत्रे "
            "तपासते, संमती मागते आणि महसूल व उच्च शिक्षण विभाग यांचे समन्वय साधते."
        ),
        goal_statement_en="I want to apply for an engineering college admission scholarship.",
        goal_statement_mr="मला इंजिनिअरिंग कॉलेज प्रवेशासाठी शिष्यवृत्ती अर्ज करायचा आहे.",
    ),
    "start_small_business": LifeEventMeta(
        code="start_small_business",
        title_en="Starting a Small Business",
        title_mr="लघु व्यवसाय सुरू करणे",
        description_en=(
            "Register a shop/establishment and obtain the local NOC and GST registration "
            "needed to legally operate — one coordinated journey across three departments."
        ),
        description_mr=(
            "दुकान/आस्थापना नोंदणी करा आणि कायदेशीररित्या व्यवसाय चालवण्यासाठी आवश्यक स्थानिक ना-हरकत "
            "प्रमाणपत्र व GST नोंदणी मिळवा — तीन विभागांमधील एक समन्वित प्रवास."
        ),
        goal_statement_en="I want to start a small business.",
        goal_statement_mr="मला लघु व्यवसाय सुरू करायचा आहे.",
    ),
}


def get_life_event_meta(code: str) -> LifeEventMeta:
    try:
        return LIFE_EVENT_CATALOG[code]
    except KeyError as exc:
        raise ValueError(f"Unknown life_event_code: {code}") from exc


def list_life_event_codes() -> list[str]:
    """Only codes that have both metadata *and* a working dependency
    graph are listed — a code with one but not the other would be a
    half-built life event, which the product should never expose."""
    return [code for code in LIFE_EVENT_CATALOG if _has_graph(code)]


def _has_graph(code: str) -> bool:
    try:
        get_graph(code)
        return True
    except ValueError:
        return False
