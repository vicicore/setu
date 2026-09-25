from dataclasses import dataclass, field


@dataclass(frozen=True)
class ServiceRequirement:
    """Explicit, inspectable requirement metadata — the answer to
    "what must be true before this service can proceed". A service with
    an empty `requires` list is a root document (its own state comes
    from a connector or the vault, not from other services)."""

    service_code: str
    requires: list[str] = field(default_factory=list)
    department: str = ""
    display_name: str = ""


class DependencyGraph:
    """In-memory representation of a life event's service requirement
    graph. The same shape is stored relationally in
    `service_dependencies` (see 0002_seed_catalog.sql — one row per
    (service, depends_on) pair, already many-to-many); this class is
    what the orchestrator and the eligibility engine both walk at
    runtime, so there is exactly one definition of "what does X require"
    in the whole system."""

    def __init__(self, requirements: list[ServiceRequirement]) -> None:
        self._by_service = {r.service_code: r for r in requirements}

    @property
    def service_codes(self) -> list[str]:
        return list(self._by_service.keys())

    def requirements_of(self, service_code: str) -> list[str]:
        """The list of service_codes that must all be VERIFIED before
        `service_code` can proceed. Empty for a root document."""
        return list(self._by_service[service_code].requires)

    def department_of(self, service_code: str) -> str:
        return self._by_service[service_code].department

    def display_name_of(self, service_code: str) -> str:
        return self._by_service[service_code].display_name

    def dependents_of(self, service_code: str) -> list[str]:
        """Services that list `service_code` as one of their requirements
        — used to walk forward when `service_code` changes state."""
        return [
            r.service_code
            for r in self._by_service.values()
            if service_code in r.requires
        ]


COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH = DependencyGraph([
    # Identity, domicile, caste and income are independent documents the
    # citizen may already hold verified copies of — each is a root
    # requirement (empty `requires`). The scholarship application is the
    # one goal service with real requirements: it needs identity,
    # domicile AND income all verified (caste is tracked but not a
    # scholarship prerequisite in this life event).
    ServiceRequirement("identity_verification", [], "Home", "Identity Verification"),
    ServiceRequirement("domicile_certificate", [], "Revenue", "Domicile Certificate"),
    ServiceRequirement("caste_certificate", [], "Social Justice", "Caste Certificate"),
    ServiceRequirement("income_certificate", [], "Revenue", "Income Certificate"),
    ServiceRequirement(
        "education_scholarship",
        ["identity_verification", "domicile_certificate", "income_certificate"],
        "Higher Education",
        "Engineering Admission Scholarship",
    ),
])

START_SMALL_BUSINESS_GRAPH = DependencyGraph([
    ServiceRequirement("business_registration", [], "Labour", "Shop & Establishment Registration"),
    ServiceRequirement("local_noc", ["business_registration"], "Urban Development", "Local Body NOC"),
    ServiceRequirement("gst_registration", ["business_registration"], "Finance", "GST Registration"),
])

# Registry keyed by the same life_event.code values seeded in
# 0002_seed_catalog.sql — lets a persisted ApplicationRecord (which
# stores only the code, not a live graph object) be reconstructed back
# into a domain Journey. See app/services/journey_mapper.py.
GRAPH_REGISTRY: dict[str, DependencyGraph] = {
    "college_admission_scholarship": COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH,
    "start_small_business": START_SMALL_BUSINESS_GRAPH,
}


def get_graph(life_event_code: str) -> DependencyGraph:
    try:
        return GRAPH_REGISTRY[life_event_code]
    except KeyError as exc:
        raise ValueError(f"Unknown life_event_code: {life_event_code}") from exc
