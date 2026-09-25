"""Fixed data describing the College Admission + Scholarship signature
demo (Master Prompt section 5 / Build README section 4). A citizen id
and a deterministic application id — rather than a freshly generated
UUID — so /demo/reset always mutates the *same* application record
instead of piling up a new one on every judge run."""

from dataclasses import dataclass

from app.services.dependency_graph import COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH, DependencyGraph

DEMO_CITIZEN_ID = "demo-citizen-priya-deshmukh"
DEMO_APPLICATION_ID = "demo-application-college-admission-scholarship"
DEMO_LIFE_EVENT_CODE = "college_admission_scholarship"
DEMO_GRAPH: DependencyGraph = COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH
ALREADY_VERIFIED_ON_RESET = {
    "identity_verification",
    "domicile_certificate",
    "caste_certificate",
}

CITIZEN_GOAL_STATEMENT_MR = "मला इंजिनिअरिंग कॉलेज प्रवेशासाठी शिष्यवृत्ती अर्ज करायचा आहे."
CITIZEN_GOAL_STATEMENT_EN = "I want to apply for an engineering college admission scholarship."


@dataclass
class CatalogServiceView:
    service_code: str
    display_name: str
    department: str
    depends_on_service_code: str | None


def catalog() -> list[CatalogServiceView]:
    return [
        CatalogServiceView(
            service_code=code,
            display_name=DEMO_GRAPH.display_name_of(code),
            department=DEMO_GRAPH.department_of(code),
            depends_on_service_code=DEMO_GRAPH.dependency_of(code),
        )
        for code in DEMO_GRAPH.service_codes
    ]
