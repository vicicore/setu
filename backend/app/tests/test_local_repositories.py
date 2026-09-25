"""Exercises the repository abstraction directly, independent of the API
or the orchestrator: proves the local/demo persistence adapter satisfies
its own interface contract, so a future SupabaseApplicationRepository
can be tested against the same expectations."""

from datetime import datetime, timezone

from app.repositories.local.application_repository import LocalJsonApplicationRepository
from app.repositories.local.audit_log_repository import LocalJsonAuditLogRepository
from app.repositories.models import ApplicationRecord, AuditLogEntry, StepRecord
from app.schemas.enums import ApplicationStepStatus


def _sample_record(record_id: str = "app-1") -> ApplicationRecord:
    now = datetime.now(timezone.utc)
    return ApplicationRecord(
        id=record_id,
        citizen_id="citizen-1",
        life_event_code="college_admission_scholarship",
        steps={
            "income_certificate": StepRecord(
                service_code="income_certificate",
                status=ApplicationStepStatus.NOT_STARTED,
                updated_at=now,
            )
        },
        created_at=now,
        updated_at=now,
    )


def test_application_repository_round_trips_and_persists_across_instances(tmp_path) -> None:
    data_dir = str(tmp_path)
    repo = LocalJsonApplicationRepository(data_dir=data_dir)
    record = _sample_record()
    repo.create(record)

    fetched = repo.get("app-1")
    assert fetched is not None
    assert fetched.citizen_id == "citizen-1"
    assert fetched.steps["income_certificate"].status == ApplicationStepStatus.NOT_STARTED

    # Mutate and save.
    fetched.steps["income_certificate"].status = ApplicationStepStatus.IN_PROGRESS
    repo.save(fetched)

    # A brand-new repository instance pointed at the same directory must
    # see the change — proves this is real file persistence, not a
    # process-local cache.
    second_instance = LocalJsonApplicationRepository(data_dir=data_dir)
    reloaded = second_instance.get("app-1")
    assert reloaded is not None
    assert reloaded.steps["income_certificate"].status == ApplicationStepStatus.IN_PROGRESS


def test_application_repository_list_and_delete(tmp_path) -> None:
    repo = LocalJsonApplicationRepository(data_dir=str(tmp_path))
    repo.create(_sample_record("app-1"))
    repo.create(_sample_record("app-2"))

    assert {r.id for r in repo.list_all()} == {"app-1", "app-2"}
    assert len(repo.list_for_citizen("citizen-1")) == 2

    repo.delete("app-1")
    assert repo.get("app-1") is None
    assert {r.id for r in repo.list_all()} == {"app-2"}


def test_audit_log_repository_appends_and_filters_by_application(tmp_path) -> None:
    repo = LocalJsonAuditLogRepository(data_dir=str(tmp_path))
    now = datetime.now(timezone.utc)
    repo.append(
        AuditLogEntry(
            application_id="app-1", actor="citizen", action="consent.granted",
            resource_type="application", created_at=now,
        )
    )
    repo.append(
        AuditLogEntry(
            application_id="app-2", actor="citizen", action="consent.granted",
            resource_type="application", created_at=now,
        )
    )

    assert len(repo.list_for_application("app-1")) == 1
    assert len(repo.list_all()) == 2
