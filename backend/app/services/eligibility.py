"""Deterministic, inspectable eligibility rules — explicitly NOT an LLM
decision (Master Prompt section 16: AI may assist with intent/explanation
but must never be the sole authority on eligibility). Every result comes
with a plain-language reason derived directly from the same requirement
graph (app/services/dependency_graph.py) the orchestrator uses once a
journey actually starts — one definition of "what does X require",
walked by both.

This is intentionally a pure function over (graph, verified_service_codes)
rather than a method on JourneyOrchestrator: eligibility is checked
*before* any Application/Consent exists, so there is no Journey object
yet for it to operate on. See docs/DECISIONS.md.

`verified_service_codes` is computed by the caller from real persisted
state (verified vault documents — see vault_eligibility.py) for the
normal citizen-facing flow; callers may still pass an explicit set for
testing or for a life event with no citizen context yet."""

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
        requirements = graph.requirements_of(service_code)
        unmet = [r for r in requirements if r not in verified_service_codes]

        if service_code in verified_service_codes:
            status = ApplicationStepStatus.VERIFIED
            reasons = [f"{display_name} is already verified."]
        elif not requirements:
            status = ApplicationStepStatus.NOT_STARTED
            reasons = [f"{display_name} has not been applied for yet."]
        elif not unmet:
            status = ApplicationStepStatus.READY
            required_names = ", ".join(graph.display_name_of(r) for r in requirements)
            reasons = [f"{required_names} verified — ready to apply for {display_name}."]
        else:
            status = ApplicationStepStatus.BLOCKED
            missing_names = ", ".join(graph.display_name_of(r) for r in unmet)
            reasons = [f"Requires {missing_names} to be verified first."]

        services.append(
            ServiceEligibility(
                service_code=service_code,
                display_name=display_name,
                department=department,
                status=status,
                requires_service_codes=requirements,
                reasons=reasons,
            )
        )

    overall_ready = all(s.status != ApplicationStepStatus.BLOCKED for s in services)

    return EligibilityEvaluateResult(
        life_event_code=life_event_code, services=services, overall_ready=overall_ready
    )
