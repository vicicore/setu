"""Turns raw Journey state into the plain-language answers a citizen
actually needs — "what's blocking me", "what do I do next". Computed
here, server-side, from real step/consent state; never fabricated in the
frontend. Priority 3 of Phase 6 explicitly requires this transformation
to happen somewhere real, not be invented as UI copy."""

from app.schemas.enums import ApplicationStepStatus
from app.services.orchestrator import Journey


def current_blocker(journey: Journey) -> str | None:
    for code, step in journey.steps.items():
        if step.status == ApplicationStepStatus.BLOCKED:
            return f"{journey.graph.display_name_of(code)}: {step.blocked_reason}"
    return None


def next_action(journey: Journey) -> str:
    if journey.is_complete():
        return "Nothing further needed — every required service for this journey is verified."

    # A rejection is the most urgent, explicit thing a citizen needs to
    # act on — surface it before a merely-not-yet-started step.
    for code, step in journey.steps.items():
        if step.status == ApplicationStepStatus.REJECTED:
            display_name = journey.graph.display_name_of(code)
            return f"{display_name} was rejected — check the reason and resubmit."

    # NOT_STARTED (never touched) and READY (its own requirements are
    # now satisfied, e.g. local_noc once business_registration verifies)
    # are both "the citizen can act on this now" states — a step that
    # only had this checked for NOT_STARTED would silently stop
    # suggesting consent/submission the moment a dependency unlocked it,
    # exactly the bug a live Small Business run caught.
    for code, step in journey.steps.items():
        if step.status not in (ApplicationStepStatus.NOT_STARTED, ApplicationStepStatus.READY):
            continue
        display_name = journey.graph.display_name_of(code)
        department = journey.graph.department_of(code)
        consent = journey.consents.get(code)
        if not consent or not consent.is_active:
            return f"Grant consent to share your data with {department} for {display_name}."
        return f"Submit {display_name} to {department}."

    for code, step in journey.steps.items():
        if step.status == ApplicationStepStatus.IN_PROGRESS:
            display_name = journey.graph.display_name_of(code)
            department = journey.graph.department_of(code)
            return f"Waiting for {department} to process {display_name}."

    return "No action needed right now."
