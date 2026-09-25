import pytest

from app.core import container
from app.core.config import get_settings

# Every lru_cache-backed factory in app/core/container.py, plus
# get_settings. Missing one here doesn't fail loudly — it just leaves a
# stale singleton (wrong tmp_path, stale connector state) silently
# shared across tests, which is exactly the kind of bug that only shows
# up as flakiness under a different test order. Keep this list exhaustive.
_CACHED_FACTORIES = [
    get_settings,
    container.get_application_repository,
    container.get_audit_log_repository,
    container.get_document_storage,
    container.get_revenue_connector,
    container.get_journey_service,
    container.get_citizen_repository,
    container.get_document_repository,
    container.get_citizen_profile_service,
    container.get_document_vault_service,
    container._connector_registry,
]


@pytest.fixture(autouse=True)
def isolated_local_data_dir(tmp_path, monkeypatch):
    """Every test gets its own throwaway data directory and a clean set
    of container singletons, so JSON-file persistence (and in-memory
    connector state) in one test can never leak into another."""
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path))
    for factory in _CACHED_FACTORIES:
        factory.cache_clear()
    yield
    for factory in _CACHED_FACTORIES:
        factory.cache_clear()
