from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyEdge:
    service_code: str
    depends_on_service_code: str | None
    department: str
    display_name: str


class DependencyGraph:
    """In-memory representation of a life event's service DAG. The same
    shape is stored relationally in `service_dependencies` (see
    0002_seed_catalog.sql); this class is what the orchestrator walks at
    runtime."""

    def __init__(self, edges: list[DependencyEdge]) -> None:
        self._edges_by_service = {edge.service_code: edge for edge in edges}

    @property
    def service_codes(self) -> list[str]:
        return list(self._edges_by_service.keys())

    def dependency_of(self, service_code: str) -> str | None:
        return self._edges_by_service[service_code].depends_on_service_code

    def department_of(self, service_code: str) -> str:
        return self._edges_by_service[service_code].department

    def display_name_of(self, service_code: str) -> str:
        return self._edges_by_service[service_code].display_name

    def dependents_of(self, service_code: str) -> list[str]:
        return [
            edge.service_code
            for edge in self._edges_by_service.values()
            if edge.depends_on_service_code == service_code
        ]


COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH = DependencyGraph([
    # Identity, domicile, caste and income are independent documents the
    # citizen may already hold verified copies of. Only the final goal
    # service (the scholarship application) is gated on a dependency —
    # here, on the income certificate being verified. This mirrors the
    # signature demo exactly: Domicile/Identity/Caste show their own
    # verification state; Income shows missing/expired; only Scholarship
    # shows BLOCKED, and only because of Income specifically.
    DependencyEdge("identity_verification", None, "Home", "Identity Verification"),
    DependencyEdge("domicile_certificate", None, "Revenue", "Domicile Certificate"),
    DependencyEdge("caste_certificate", None, "Social Justice", "Caste Certificate"),
    DependencyEdge("income_certificate", None, "Revenue", "Income Certificate"),
    DependencyEdge("education_scholarship", "income_certificate", "Higher Education", "Engineering Admission Scholarship"),
])

START_SMALL_BUSINESS_GRAPH = DependencyGraph([
    DependencyEdge("business_registration", None, "Labour", "Shop & Establishment Registration"),
    DependencyEdge("local_noc", "business_registration", "Urban Development", "Local Body NOC"),
    DependencyEdge("gst_registration", "business_registration", "Finance", "GST Registration"),
])
