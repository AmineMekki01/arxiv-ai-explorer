import pytest
from fastapi.testclient import TestClient

import src.main as main_mod

pytestmark = pytest.mark.unit

class TestMainRoutes:
    """Tests for top-level utility routes defined in src.main."""

    def test_root_endpoint(self):
        """Root endpoint should return welcome payload with version info."""
        client = TestClient(main_mod.app)

        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Welcome" in data["message"]
        assert data["version"] == main_mod.settings.app_version
        assert data["health"] == "/health"

    def test_health_endpoint(self):
        """Simple health endpoint should always report healthy status."""
        client = TestClient(main_mod.app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == main_mod.settings.app_version

    def test_detailed_health_check_healthy(self, monkeypatch):
        """When DB check succeeds, detailed health should be healthy."""

        async def fake_check_ok() -> bool:
            return True

        monkeypatch.setattr(main_mod, "check_database_connection", fake_check_ok)

        client = TestClient(main_mod.app)
        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["services"]["postgresql"] == "healthy"
        assert data["version"] == main_mod.settings.app_version

    def test_detailed_health_check_unhealthy(self, monkeypatch):
        """When DB check fails, detailed health should be degraded."""

        async def fake_check_fail() -> bool:
            return False

        monkeypatch.setattr(main_mod, "check_database_connection", fake_check_fail)

        client = TestClient(main_mod.app)
        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["postgresql"] == "unhealthy"

    def test_test_database_success(self, monkeypatch):
        """/test/database should return success when DB check passes."""

        async def fake_check_ok() -> bool:
            return True

        monkeypatch.setattr(main_mod, "check_database_connection", fake_check_ok)

        client = TestClient(main_mod.app)
        response = client.get("/test/database")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "successful" in data["message"].lower()

    def test_test_database_failure(self, monkeypatch):
        """/test/database should return 500 when DB check returns False."""

        async def fake_check_fail() -> bool:
            return False

        monkeypatch.setattr(main_mod, "check_database_connection", fake_check_fail)

        client = TestClient(main_mod.app)
        response = client.get("/test/database")

        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Database connection failed"

    def test_test_database_exception(self, monkeypatch):
        """/test/database should wrap DB errors into HTTP 500."""

        async def fake_check_raises() -> bool:
            raise RuntimeError("boom")

        monkeypatch.setattr(main_mod, "check_database_connection", fake_check_raises)

        client = TestClient(main_mod.app)
        response = client.get("/test/database")

        assert response.status_code == 500
        data = response.json()
        assert "Database error:" in data["detail"]


@pytest.mark.asyncio
async def test_general_exception_handler_returns_500():
    """General exception handler should always return a 500 JSON response."""
    response = await main_mod.general_exception_handler(object(), RuntimeError("boom"))

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "Internal server error"


@pytest.mark.asyncio
async def test_lifespan_success(monkeypatch):
    """lifespan should run startup and shutdown steps when DB is available."""

    async def fake_check_ok() -> bool:
        return True

    async def fake_create_tables() -> None:
        return None

    closed = {"called": False}

    def fake_close_shared_driver() -> None:
        closed["called"] = True

    monkeypatch.setattr(main_mod, "check_database_connection", fake_check_ok)
    monkeypatch.setattr(main_mod, "create_tables", fake_create_tables)
    monkeypatch.setattr(main_mod, "close_shared_driver", fake_close_shared_driver)

    async with main_mod.lifespan(main_mod.app):
        assert True

    assert closed["called"] is True


@pytest.mark.asyncio
async def test_lifespan_raises_when_db_unavailable(monkeypatch):
    """lifespan should raise when the database cannot be reached."""

    async def fake_check_fail() -> bool:
        return False

    monkeypatch.setattr(main_mod, "check_database_connection", fake_check_fail)

    with pytest.raises(RuntimeError):
        async with main_mod.lifespan(main_mod.app):
            pass
