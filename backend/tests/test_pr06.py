from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_session
from app.auth.dependencies import get_current_user
from app.auth.schemas import CurrentUser
from app.models import Base,User,VideoSnapshot,Score
from app.sync.bilibili_crawler import VIDEO_CACHE, crawl_videos, get_cached_video
from app.api.video_data import extract_bv


@pytest.fixture
def client_db(tmp_path):
    engine=create_engine("sqlite:///"+(tmp_path/"api.db").as_posix(),connect_args={"check_same_thread":False})
    Base.metadata.create_all(engine)
    factory=sessionmaker(engine)
    today=datetime.now(timezone(timedelta(hours=8))).date()
    with factory() as s:
        s.add(User(username="test",password_hash="not-returned",display_name="测试",role="member",is_active=True))
        for i in range(7):
            v=VideoSnapshot(feishu_record_id=str(i),up_name="UP",video_title="=标题" if i==0 else "视频",publish_date=today-timedelta(days=i),raw_payload={"fields":{"BV号":{"value":[{"text":"BV1234567890"}]},"编导":{"value":["编导甲"]},"播放量":{"value":[100]},"3s跳出率":.2,"播转粉率":"1%"},"private":"secret-marker"},last_modified_at=datetime.now())
            s.add(v);s.flush()
            s.add(Score(video_snapshot_id=v.id,score=86+i,score_detail={"private":"secret-marker"},algorithm_version="v1.0"))
        s.commit()
    def db():
        with factory() as s:yield s
    app.dependency_overrides[get_session]=db
    try:
        with TestClient(app) as c:yield c,engine,factory
    finally:
        app.dependency_overrides.pop(get_session,None)
        app.dependency_overrides.pop(get_current_user,None)
        VIDEO_CACHE.clear();engine.dispose()


def role(name):
    app.dependency_overrides[get_current_user]=lambda:CurrentUser(id=1,username=name,display_name=name,role=name)


def test_member_projection_and_dashboard(client_db):
    c,engine,_=client_db
    assert c.get("/api/member/scores").status_code==401
    role("member")
    queries=[]
    def capture(conn,cursor,statement,parameters,context,executemany):queries.append(statement)
    event.listen(engine,"before_cursor_execute",capture)
    r=c.get("/api/member/scores",params={"page_size":2,"director":"编导甲"})
    assert r.status_code==200
    assert r.json()["total"]==7 and len(r.json()["items"])==2
    assert "score_detail" not in r.text and "raw_payload" not in r.text and "secret-marker" not in r.text
    assert all("score_detail" not in q for q in queries)
    data=c.get("/api/member/dashboard").json()
    assert len(data["top_videos"])==5 and "bv_id" not in data["top_videos"][0]
    assert data["videos"][0]["is_high_score"] is True
    assert data["videos"][0]["bv_id"]=="BV1234567890"
    for path in ("/api/admin/scores","/api/admin/users","/api/admin/export/csv","/api/admin/configs"):
        assert c.get(path).status_code==403
    assert c.put("/api/admin/users/1/role",json={"role":"admin"}).status_code==403
    assert c.get("/api/member/scores",params={"date_from":"2026-12-01","date_to":"2026-01-01"}).status_code==422


def test_admin_scores_users_export(client_db):
    c,_,factory=client_db;role("admin")
    r=c.get("/api/admin/scores");assert r.status_code==200
    assert r.json()["items"][0]["score_detail"]=={"private":"secret-marker"}
    assert "password_hash" not in c.get("/api/admin/users").text
    assert c.put("/api/admin/users/1/role",json={"role":"other"}).status_code==422
    assert c.put("/api/admin/users/999/role",json={"role":"member"}).status_code==404
    assert c.put("/api/admin/users/1/role",json={"role":"admin"}).status_code==200
    with factory() as s: assert s.get(User,1).role=="admin"
    r=c.get("/api/admin/export/csv");assert r.status_code==200
    assert "'=标题" in r.text and "secret-marker" not in r.text


def test_crawler_partial_failure_and_copy(caplog):
    def handler(request):
        bv=request.url.params["bvid"]
        if bv=="BV0000000000":return httpx.Response(200,json={"code":-404,"message":"不存在"})
        return httpx.Response(200,json={"code":0,"data":{"title":"标题","owner":{"name":"UP"},"pubdate":1700000000,"pic":"https://example.test/pic","stat":{"view":100,"like":1,"coin":2,"favorite":3,"reply":4,"share":5,"danmaku":6,"now_rank":0,"his_rank":2}}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        result=crawl_videos(["BV1234567890","BV0000000000"],c)
    assert len(result)==1 and result["BV1234567890"]["coin_count"]==2
    assert "-404" in caplog.text
    VIDEO_CACHE.update(result)
    copy=get_cached_video("BV1234567890");copy["ranking_status"]["historical_rank"]=99
    assert get_cached_video("BV1234567890")["ranking_status"]["historical_rank"]==2
    VIDEO_CACHE.clear()


def test_bv_link_fallback():
    assert extract_bv({"fields":{"标题":{"value":[{"link":"https://www.bilibili.com/video/BV1234567890/"}]}}})=="BV1234567890"


def test_dashboard_null_scores_and_date_order(client_db):
    from sqlalchemy import delete
    c,_,factory=client_db
    with factory() as session:
        session.execute(delete(Score));session.commit()
    role("member")
    response=c.get("/api/member/dashboard")
    assert response.status_code==200
    data=response.json()
    assert data["top_videos"]==[]
    assert all(v["score"] is None for v in data["videos"])
    dates=[v["publish_date"] for v in data["videos"]]
    assert dates==sorted(dates,reverse=True)
