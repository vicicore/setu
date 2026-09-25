"""Deterministic, inspectable eligibility rules — explicitly NOT an LLM
decision (Master Prompt section 16: AI may assist with intent/explanation
but must never be the sole authority on eligibility). Every result comes
with a plain-language reason derived directly from the dependency graph,
the same graph the orchestrator uses once a journey actually starts.

This is intentionally a pure function over (graph, verified_service_codes)
rather than a method on JourneyOrchestrator: eligibility is checked
*before* any Application/Consent exists, so there is no Journey object
yet for it to operate on. See docs/DECISIONS.md."""

from app.schemas.enums import ApplicationStepStatus
from app.schemas.eligibility import EligibilityEvaluateResult, ServiceEligibility
from app.services.dependency_graph import DependencyGraph


def evaluate(
    life_event_code: str, graph: DependencyGraph, verified_service_codes: set[str]
) -> EligibilityEvaluateResult:
    services: list[ServiceEligibility] = []

    for service_code in graph.service_codes:
        display_name = graph.display_name_of(service_code)
        department = graph.department_of(service_code)
        dependency = graph.dependency_of(service_code)

        if service_code in verified_service_codes:
            status = ApplicationStepStatus.VERIFIED
            reasons = [f"{display_name} is already verified."]
        elif dependency is None:
            status = ApplicationStepStatus.NOT_STARTED
            reasons = [f"{display_name} has not been applied for yet."]
        elif dependency in verified_service_codes:
            status = ApplicationStepStatus.READY
            reasons = [f"{graph.display_name_of(dependency)} is verified — ready to apply for {display_name}."]
        else:
            status = ApplicationStepStatus.BLOCKED
            reasons = [f"Requires {graph.display_name_of(dependency)} to be verified first."]

        services.append(
            ServiceEligibility(
                service_code=service_code,
                display_name=display_name,
                department=department,
                status=status,
                depends_on_service_code=dependency,
                reasons=reasons,
            )
        )

    overall_ready = all(s.status != ApplicationStepStatus.BLOCKED for s in services)

    return EligibilityEvaluateResult(
        life_event_code=life_event_code, services=services, overall_ready=overall_ready
    )
