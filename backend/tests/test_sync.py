import json
import logging
import secrets
from threading import Event
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.models import Base, VideoSnapshot
from app.sync.feishu_client import FeishuClient, FeishuError
from app.sync.task import SyncService
from app.main import app
from app.auth.dependencies import get_current_user
from app.auth.schemas import CurrentUser


@pytest.fixture
def setup_sync(tmp_path):
    engine = create_engine("sqlite:///" + (tmp_path / "sync.db").as_posix())
    Base.metadata.create_all(engine)
    settings = SimpleNamespace(FEISHU_APP_ID=secrets.token_hex(8), FEISHU_APP_SECRET=secrets.token_hex(16), FEISHU_APP_TOKEN=secrets.token_hex(8), FEISHU_TABLE_ID=secrets.token_hex(8), FEISHU_UP_NAME_FIELD="up主", FEISHU_TITLE_FIELD="标题", FEISHU_PUBLISH_DATE_FIELD="发布时间", FEISHU_SYNC_ENABLED=False, SYNC_INTERVAL_MINUTES=15)
    yield settings, sessionmaker(engine)
    engine.dispose()


def record(record_id="record1", modified=1700000000123, title="测试标题"):
    # 仅测试 HTTP 响应，不生成或写入业务种子数据。
    return {"record_id": record_id, "last_modified_time": modified, "fields": {"up主": {"type": 1, "value": ["测试UP"]}, "标题": {"type": 1, "value": [{"text": title}]}, "发布时间": {"type": 5, "value": [1690000000000]}}}


def make_service(setup_sync, handler):
    settings, factory = setup_sync
    return SyncService(settings, factory, lambda s: FeishuClient(s, httpx.MockTransport(handler)))


def test_pagination_incremental_upsert(setup_sync):
    current = record()
    cursors = []
    def handler(request):
        if request.url.path.endswith("/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "test-token"})
        assert request.url.params["page_size"] == "500"
        assert json.loads(request.content)["automatic_fields"] is True
        cursor = request.url.params.get("page_token")
        cursors.append(cursor)
        return httpx.Response(200, json={"code": 0, "data": {"items": [current if cursor is None else record("record2")], "has_more": cursor is None, "page_token": "next" if cursor is None else None}})
    service = make_service(setup_sync, handler)
    try:
        service._run()
        assert service.status()["inserted"] == 2
        service._run()
        assert service.status()["inserted"] == service.status()["updated"] == 0
        current = record(modified=1700000000456, title="同秒更新")
        service._run()
        assert service.status()["updated"] == 1
        with setup_sync[1]() as session:
            rows = session.scalars(select(VideoSnapshot)).all()
            assert len(rows) == 2
            assert rows[0].raw_payload == current
        assert cursors == [None, "next"] * 3
    finally:
        service.close()


def test_failure_rollback_and_recovery(setup_sync, caplog):
    fail = True
    def handler(request):
        if request.url.path.endswith("/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "test-token"})
        if request.url.params.get("page_token"):
            return httpx.Response(403, json={"code": 1254302, "msg": "permission denied"})
        return httpx.Response(200, json={"code": 0, "data": {"items": [record()], "has_more": fail, "page_token": "next"}})
    service = make_service(setup_sync, handler)
    try:
        with caplog.at_level(logging.INFO):
            service._run()
        status = service.status()
        assert status["success"] is False
        assert status["inserted"] == 0
        assert "HTTP=403 code=1254302 message=permission denied" in status["error"]
        assert "permission denied" in caplog.text
        with setup_sync[1]() as session:
            assert session.scalar(select(VideoSnapshot)) is None
        fail = False
        service._run()
        assert service.status()["success"] is True
    finally:
        service.close()


@pytest.mark.parametrize("failure", ["repeat_cursor", "invalid_json", "timeout", "api_error"])
def test_client_errors(setup_sync, failure):
    def handler(request):
        if request.url.path.endswith("/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "test-token"})
        if failure == "timeout":
            raise httpx.ReadTimeout("private URL", request=request)
        if failure == "invalid_json":
            return httpx.Response(502, text="not json")
        if failure == "api_error":
            return httpx.Response(200, json={"code": 123, "msg": setup_sync[0].FEISHU_APP_SECRET})
        return httpx.Response(200, json={"code": 0, "data": {"items": [], "has_more": True, "page_token": "same"}})
    with pytest.raises(FeishuError) as error:
        list(FeishuClient(setup_sync[0], httpx.MockTransport(handler)).records())
    assert setup_sync[0].FEISHU_APP_SECRET not in str(error.value)


def test_trigger_nonblocking_and_no_overlap(setup_sync):
    entered, release = Event(), Event()
    service = SyncService(*setup_sync)
    def run():
        entered.set()
        release.wait(5)
    service._run = run
    try:
        assert service.trigger()
        assert entered.wait(2)
        assert service.status()["running"]
        assert not service.trigger()
    finally:
        release.set()
        service.close()


def test_admin_only_routes():
    try:
        with TestClient(app) as client:
            assert client.get("/api/admin/sync/status").status_code == 401
            for role, expected in [("member", 403), ("admin", 200)]:
                app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=1, username=role, display_name=role, role=role)
                assert client.get("/api/admin/sync/status").status_code == expected
                if role == "member":
                    assert client.post("/api/admin/sync/run").status_code == 403
            app.state.sync_service.trigger = lambda: True
            assert client.post("/api/admin/sync/run").status_code == 202
            app.state.sync_service.trigger = lambda: False
            assert client.post("/api/admin/sync/run").status_code == 409
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_skip_missing_required_fields(setup_sync, caplog):
    def handler(request):
        if request.url.path.endswith("/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "test-token"})
        return httpx.Response(200, json={"code": 0, "data": {"items": [record(), {"record_id": "empty", "last_modified_time": 1700000000123, "fields": {}}], "has_more": False}})
    service = make_service(setup_sync, handler)
    try:
        with caplog.at_level(logging.INFO):
            service._run()
        assert service.status()["success"] is True
        assert service.status()["fetched"] == 2
        assert service.status()["inserted"] == 1
        assert service.status()["skipped"] == 1
        assert "record_id=empty" in caplog.text
        service._run()
        assert service.status()["inserted"] == service.status()["updated"] == 0
    finally:
        service.close()
