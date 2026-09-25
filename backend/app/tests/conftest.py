import pytest

from app.core import container
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def isolated_local_data_dir(tmp_path, monkeypatch):
    """Every test gets its own throwaway data directory and a clean set
    of container singletons, so JSON-file persistence in one test can
    never leak into another."""
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    container.get_application_repository.cache_clear()
    container.get_audit_log_repository.cache_clear()
    container.get_document_storage.cache_clear()
    container.get_revenue_connector.cache_clear()
    container.get_journey_service.cache_clear()
    yield
    get_settings.cache_clear()
    container.get_application_repository.cache_clear()
    container.get_audit_log_repository.cache_clear()
    container.get_document_storage.cache_clear()
    container.get_revenue_connector.cache_clear()
    container.get_journey_service.cache_clear()
