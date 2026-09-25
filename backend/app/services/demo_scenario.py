"""Fixed data describing the College Admission + Scholarship signature
demo (Master Prompt section 5 / Build README section 4). A citizen id
and a deterministic application id — rather than a freshly generated
UUID — so /demo/reset always mutates the *same* application record
instead of piling up a new one on every judge run."""

from dataclasses import dataclass

from app.services.dependency_graph import COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH, DependencyGraph
from app.services.document_service import DocumentVaultService

DEMO_CITIZEN_ID = "demo-citizen-priya-deshmukh"
DEMO_APPLICATION_ID = "demo-application-college-admission-scholarship"
DEMO_LIFE_EVENT_CODE = "college_admission_scholarship"
DEMO_GRAPH: DependencyGraph = COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH

# Verified up front, through the vault lifecycle, every reset.
_SEED_VERIFIED_DOC_TYPES = ["identity_verification", "domicile_certificate"]
# Uploaded but deliberately left un-reviewed — this is the one the /demo
# UI walks through "Submit for Review" -> "Verify" live, to make the
# vault -> eligibility -> journey cascade visible without touching the
# required income/scholarship path (income_certificate has no vault
# document at all; it only exists via the Revenue connector).
SEED_PENDING_DOC_TYPE = "caste_certificate"

CITIZEN_GOAL_STATEMENT_MR = "मला इंजिनिअरिंग कॉलेज प्रवेशासाठी शिष्यवृत्ती अर्ज करायचा आहे."
CITIZEN_GOAL_STATEMENT_EN = "I want to apply for an engineering college admission scholarship."


@dataclass
class CatalogServiceView:
    service_code: str
    display_name: str
    department: str
    requires_service_codes: list[str]


def catalog() -> list[CatalogServiceView]:
    return [
        CatalogServiceView(
            service_code=code,
            display_name=DEMO_GRAPH.display_name_of(code),
            department=DEMO_GRAPH.department_of(code),
            requires_service_codes=DEMO_GRAPH.requirements_of(code),
        )
        for code in DEMO_GRAPH.service_codes
    ]


def reset_demo_vault(vault: DocumentVaultService) -> None:
    """Wipes and reseeds the demo citizen's vault so /demo/reset is
    fully deterministic: identity + domicile go through the real
    upload -> submit_for_review -> verify lifecycle and land VERIFIED;
    caste is uploaded and left at UPLOADED so it can be walked through
    live. income_certificate is intentionally absent — it only exists
    once submitted through the Revenue connector."""
    for existing in vault.list_for_citizen(DEMO_CITIZEN_ID):
        vault.delete(existing.id)

    for doc_type in _SEED_VERIFIED_DOC_TYPES:
        record = vault.upload(
            citizen_id=DEMO_CITIZEN_ID,
            file_bytes=b"%PDF-1.4 demo seed document\n",
            filename=f"{doc_type}.pdf",
            mime_type="application/pdf",
            doc_type=doc_type,
            issuer="SETU Demo Seed",
        )
        vault.submit_for_review(record.id)
        vault.verify(record.id)

    vault.upload(
        citizen_id=DEMO_CITIZEN_ID,
        file_bytes=b"%PDF-1.4 demo seed document\n",
        filename=f"{SEED_PENDING_DOC_TYPE}.pdf",
        mime_type="application/pdf",
        doc_type=SEED_PENDING_DOC_TYPE,
        issuer="SETU Demo Seed",
    )
