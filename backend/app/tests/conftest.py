import itertools

import pytest
from fastapi.testclient import TestClient

from app.core import container
from app.core.config import get_settings

_identifier_counter = itertools.count()


def login(client: TestClient, identifier: str | None = None) -> tuple[str, dict[str, str]]:
    """Logs in (registering on first use) via the real POST /auth/session
    endpoint and returns (citizen_id, headers) — every test that needs an
    authenticated citizen uses this instead of inventing a citizen_id
    string, since the backend now derives citizen_id from the login
    identifier and no longer accepts a caller-supplied one."""
    if identifier is None:
        identifier = f"test-citizen-{next(_identifier_counter)}"
    response = client.post("/api/v1/auth/session", json={"identifier": identifier})
    body = response.json()
    return body["citizen_id"], {"Authorization": f"Bearer {body['token']}"}


def login_admin(client: TestClient) -> tuple[str, dict[str, str]]:
    return login(client, identifier="admin")

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
    container.get_connector_request_repository,
    container.get_auth_repository,
    container.get_auth_service,
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
