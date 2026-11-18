from unittest.mock import MagicMock
from threading import Event
from app.sync.refresh_all import RefreshService


def test_complete_refresh_and_coalescing(monkeypatch):
    gate = Event()
    sync = MagicMock()
    sync.trigger.side_effect = lambda: gate.wait(2)
    sync.status.return_value = {"running": False, "success": True}
    cache = MagicMock()
    cache.refresh.return_value = {"status": "success"}
    calculate = MagicMock(return_value={"status": "partial_success", "issues": ["secret"]})
    monkeypatch.setattr("app.sync.refresh_all.sync_and_calculate", calculate)
    highlights = MagicMock()
    monkeypatch.setattr("app.api.scores.weekly_highlights", highlights)
    service = RefreshService(sync, cache, MagicMock())
    job = service.trigger()
    assert service.trigger()["id"] == job["id"]
    gate.set()
    service.close()
    result = service.status(job["id"])
    assert result["status"] == "partial_success"
    assert "secret" not in str(result)
    calculate.assert_called_once_with(service.session_factory, force_daily=True)
    highlights.assert_called_once()


def test_sync_failure_stops_pipeline(monkeypatch):
    sync = MagicMock()
    sync.trigger.return_value = True
    sync.status.return_value = {"running": False, "success": False}
    cache = MagicMock()
    calculate = MagicMock()
    monkeypatch.setattr("app.sync.refresh_all.sync_and_calculate", calculate)
    service = RefreshService(sync, cache, MagicMock())
    job = service.trigger()
    service.close()
    assert service.status(job["id"])["status"] == "failed"
    cache.refresh.assert_not_called()
    calculate.assert_not_called()


def test_refresh_routes_auth_and_safe_status():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.refresh import router
    from app.auth.dependencies import get_current_user
    app = FastAPI()
    app.include_router(router)
    app.state.refresh_service = MagicMock()
    app.state.refresh_service.trigger.return_value = {"id": "test", "status": "running"}
    app.state.refresh_service.status.return_value = {"id": "test", "status": "success"}
    with TestClient(app) as client:
        assert client.post("/api/refresh-all").status_code == 401
        for role in ("member", "admin"):
            app.dependency_overrides[get_current_user] = lambda: {"role": role}
            assert client.post("/api/refresh-all").status_code == 202
            assert client.get("/api/refresh-all/test").json() == {"id": "test", "status": "success"}
        app.state.refresh_service.status.return_value = None
        assert client.get("/api/refresh-all/missing").status_code == 404
