import json
from datetime import date, datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, inspect
from sqlalchemy.orm import sessionmaker

from app.models import Base, AlgorithmConfig, VideoSnapshot, Score
from app.scoring.calculator import calculate_video_score, parse_metric_value, ConfigurationError
from app.scoring.initialize_configs import read_initial_rules, initialize_configs
from app.scoring.task import sync_and_calculate
from app.database import get_session
from app.auth.dependencies import get_current_user
from app.auth.schemas import CurrentUser
from app.main import app

STANDARDS = {"play": [1000,5000,10000,50000,100000], "interact": [.01,.02,.05,.1,.2], "jump_3s": [.05,.1,.2,.3,.4], "progress": [.1,.2,.4,.6,.8], "convert": [.001,.002,.005,.01,.02]}
VIDEO = dict(play=10000., interact=.05, jump_3s=.2, progress=.4, convert=.005, difficulty="S", efficiency="按时", tags=["全站"], traffic_ratio=.4)


def test_fixed_sample():
    result=calculate_video_score(VIDEO,STANDARDS,read_initial_rules())
    assert result["base_score"] == result["final_score"] == 72.0
    assert result["status"] == "success"
    for name in ("play_score","interact_score","jump_score","progress_score","convert_score"):
        assert result["score_details"][name] == 65
    assert result["bonus_and_penalty"] == {"ranking_bonus":5,"traffic_penalty":-5}


@pytest.mark.parametrize("value,expected", [(None,None),("",None),("  ",None),(0,0),(.2,.2),("20.38%",.2038),("1599.8万",15998000),("123",123)])
def test_parse(value,expected):
    assert parse_metric_value(value) == (pytest.approx(expected) if expected is not None else None)


def test_missing_and_config_changes():
    rules=read_initial_rules()
    assert calculate_video_score({**VIDEO,"play":None},STANDARDS,rules)["final_score"] is None
    assert calculate_video_score({**VIDEO,"difficulty":None},STANDARDS,rules)["status"] == "partial_success"
    rules["weight_play"] = .5
    assert calculate_video_score(VIDEO,STANDARDS,rules)["final_score"] == 78.5
    del rules["weight_play"]
    with pytest.raises(ConfigurationError): calculate_video_score(VIDEO,STANDARDS,rules)
    with pytest.raises(ConfigurationError): calculate_video_score(VIDEO,{**STANDARDS,"jump_3s":list(reversed(STANDARDS["jump_3s"]))},read_initial_rules())


@pytest.fixture
def database(tmp_path):
    engine=create_engine("sqlite:///"+(tmp_path/"scoring.db").as_posix())
    Base.metadata.create_all(engine)
    factory=sessionmaker(engine)
    with factory() as session:
        initialize_configs(session)
    yield engine,factory
    engine.dispose()


def test_task_updates_and_missing_baseline(database):
    engine,factory=database
    now=datetime(2026,11,10,tzinfo=timezone.utc)
    with factory() as session:
        fields={key:key for key in VIDEO}
        session.scalar(select(AlgorithmConfig).where(AlgorithmConfig.config_key=="metric_fields")).config_value=json.dumps(fields)
        session.add_all([VideoSnapshot(feishu_record_id=name,up_name="测试UP",video_title=name,publish_date=published,raw_payload={"fields":VIDEO},last_modified_at=now.replace(tzinfo=None)) for name,published in [("eligible",date(2026,10,26)),("young",date(2026,10,27))]])
        session.commit()
    assert sync_and_calculate(factory,now)["skipped"] == 1
    with factory() as session:
        assert session.scalar(select(Score)) is None
        session.add(AlgorithmConfig(config_key="up_standards_测试UP",config_value=json.dumps(STANDARDS)))
        session.commit()
    assert sync_and_calculate(factory,now)["calculated"] == 1
    assert sync_and_calculate(factory,now)["unchanged"] == 1
    with factory() as session:
        score=session.scalar(select(Score));score_id=score.id
        assert float(score.score)==72
        video=session.scalar(select(VideoSnapshot).where(VideoSnapshot.feishu_record_id=="eligible"))
        video.raw_payload={"fields":{**VIDEO,"tags":["每周必看"]}}
        session.commit()
    assert sync_and_calculate(factory,now)["calculated"] == 1
    with factory() as session:
        rows=session.scalars(select(Score)).all()
        assert len(rows)==1 and rows[0].id==score_id
        assert float(rows[0].score)==77
        session.scalar(select(AlgorithmConfig).where(AlgorithmConfig.config_key=="weight_play")).config_value="0.5"
        session.commit()
    assert sync_and_calculate(factory,now)["calculated"] == 1


def test_admin_config_permissions(database):
    _,factory=database
    def db():
        with factory() as session: yield session
    app.dependency_overrides[get_session]=db
    try:
        with TestClient(app) as client:
            assert client.get("/api/admin/configs").status_code==401
            app.dependency_overrides[get_current_user]=lambda:CurrentUser(id=1,username="member",display_name="成员",role="member")
            assert client.get("/api/admin/configs").status_code==403
            assert client.put("/api/admin/configs/weight_play",json={"config_value":.4}).status_code==403
            app.dependency_overrides[get_current_user]=lambda:CurrentUser(id=1,username="admin",display_name="管理员",role="admin")
            assert client.put("/api/admin/configs/up_standards_测试UP",json={"config_value":STANDARDS}).status_code==200
            assert client.put("/api/admin/configs/weight_play",json={"config_value":-.1}).status_code==422
            assert client.get("/api/admin/configs").status_code==200
    finally:
        app.dependency_overrides.pop(get_session,None)
        app.dependency_overrides.pop(get_current_user,None)


def test_unique_migration_roundtrip(tmp_path,monkeypatch):
    from app.config import get_settings
    url="sqlite:///"+(tmp_path/"migration.db").as_posix()
    monkeypatch.setattr(get_settings(),"DATABASE_URL",url)
    cfg=Config("alembic.ini")
    command.upgrade(cfg,"head")
    engine=create_engine(url)
    assert any(c["column_names"]==["video_snapshot_id","algorithm_version"] for c in inspect(engine).get_unique_constraints("scores"))
    command.downgrade(cfg,"92bc01ba8d6d")
    assert not inspect(engine).get_unique_constraints("scores")
    command.upgrade(cfg,"head")
    command.check(cfg)
    engine.dispose()


def test_batch_import_atomic_and_permissions(database):
    _,factory=database
    def db():
        with factory() as session: yield session
    app.dependency_overrides[get_session]=db
    body=[{"up_name":"批量测试",**STANDARDS}]
    try:
        with TestClient(app) as client:
            assert client.post("/api/admin/configs/import-standards",json=body).status_code==401
            app.dependency_overrides[get_current_user]=lambda:CurrentUser(id=1,username="member",display_name="成员",role="member")
            assert client.post("/api/admin/configs/import-standards",json=body).status_code==403
            app.dependency_overrides[get_current_user]=lambda:CurrentUser(id=1,username="admin",display_name="管理员",role="admin")
            assert client.post("/api/admin/configs/import-standards",json=body).json()=={"imported":1,"created":1,"updated":0}
            assert client.post("/api/admin/configs/import-standards",json=body).json()=={"imported":1,"created":0,"updated":1}
            invalid=[{"up_name":"不可部分写入",**STANDARDS},{"up_name":"错误",**STANDARDS,"play":[5,4,3,2,1]}]
            assert client.post("/api/admin/configs/import-standards",json=invalid).status_code==422
            assert client.post("/api/admin/configs/import-standards",json=body*2).status_code==422
            with factory() as session:
                assert session.scalar(select(AlgorithmConfig).where(AlgorithmConfig.config_key=="up_standards_不可部分写入")) is None
    finally:
        app.dependency_overrides.pop(get_session,None)
        app.dependency_overrides.pop(get_current_user,None)
