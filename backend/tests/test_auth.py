from datetime import datetime, timedelta, timezone
import secrets

import bcrypt
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import Session

from app.auth.security import create_access_token
from app.config import get_settings
from app.database import get_session
from app.main import app
from app.models import Base, User


@pytest.fixture
def auth_client(tmp_path):
    # 测试用户仅写入 pytest 临时数据库，不污染本地运行数据。
    engine = create_engine("sqlite:///" + (tmp_path / "auth.db").as_posix(), connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    password = secrets.token_urlsafe(24)
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with Session(engine) as session:
        session.add_all([User(username=name, display_name=name, password_hash=password_hash, role=role, is_active=active) for name, role, active in [("admin", "admin", True), ("member", "member", True), ("disabled", "member", False)]])
        session.commit()
        ids = dict(session.execute(select(User.username, User.id)).all())

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            yield client, password, ids, engine
    finally:
        app.dependency_overrides.pop(get_session, None)
        engine.dispose()


def login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def header(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_and_me(auth_client):
    client, password, ids, _ = auth_client
    response = login(client, "member", password)
    assert response.status_code == 200
    assert set(response.json()) == {"access_token", "token_type"}
    assert response.json()["token_type"] == "bearer"
    assert "set-cookie" not in response.headers
    token = response.json()["access_token"]
    claims = jwt.decode(token, get_settings().JWT_SECRET, algorithms=["HS256"])
    assert claims["sub"] == str(ids["member"])
    assert claims["exp"] - claims["iat"] == get_settings().JWT_EXPIRE_MINUTES * 60
    assert "role" not in claims
    response = client.get("/api/me", headers=header(token))
    assert response.json() == {"id": ids["member"], "username": "member", "display_name": "member", "role": "member"}


@pytest.mark.parametrize("username,correct", [("admin", False), ("unknown", True), ("disabled", True)])
def test_login_uniform_failure(auth_client, username, correct):
    client, password, _, _ = auth_client
    response = login(client, username, password if correct else secrets.token_urlsafe(24))
    assert response.status_code == 401
    assert response.json() == {"detail": "用户名或密码错误"}


@pytest.mark.parametrize("role,status", [("member", 403), ("admin", 200)])
def test_admin_permission(auth_client, role, status):
    client, password, _, _ = auth_client
    token = login(client, role, password).json()["access_token"]
    response = client.get("/api/admin/ping", headers=header(token))
    assert response.status_code == status
    if status == 200:
        assert response.json() == {"ok": True}


def test_missing_and_non_header_tokens(auth_client):
    client, _, ids, _ = auth_client
    token = create_access_token(ids["admin"])
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", params={"access_token": token}).status_code == 401
    client.cookies.set("access_token", token)
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/admin/ping").status_code == 401


@pytest.mark.parametrize("kind", ["expired", "signature", "missing_exp", "bad_subject", "deleted", "algorithm", "malformed"])
def test_invalid_tokens(auth_client, kind):
    client, _, ids, _ = auth_client
    now = datetime.now(timezone.utc)
    payload = {"sub": str(ids["admin"]), "iat": now, "exp": now + timedelta(minutes=5)}
    secret = get_settings().JWT_SECRET
    if kind == "expired":
        payload["exp"] = now - timedelta(seconds=1)
    elif kind == "signature":
        secret = secrets.token_urlsafe(48)
    elif kind == "missing_exp":
        del payload["exp"]
    elif kind == "bad_subject":
        payload["sub"] = "9" * 100
    elif kind == "deleted":
        payload["sub"] = "999999"
    token = jwt.encode(payload, secret, algorithm="HS384" if kind == "algorithm" else "HS256")
    response = client.get("/api/me", headers=header("invalid" if kind == "malformed" else token))
    assert response.status_code == 401


def test_current_database_permissions(auth_client):
    client, _, ids, engine = auth_client
    token = create_access_token(ids["admin"])
    with Session(engine) as session:
        session.execute(update(User).where(User.id == ids["admin"]).values(role="member"))
        session.commit()
    assert client.get("/api/admin/ping", headers=header(token)).status_code == 403
    with Session(engine) as session:
        session.execute(update(User).where(User.id == ids["admin"]).values(is_active=False))
        session.commit()
    assert client.get("/api/me", headers=header(token)).status_code == 401
    with Session(engine) as session:
        session.execute(delete(User).where(User.id == ids["admin"]))
        session.commit()
    assert client.get("/api/me", headers=header(token)).status_code == 401


def test_long_password_rejected(auth_client):
    client, password, _, _ = auth_client
    assert login(client, "admin", password + "x" * 73).status_code == 401


def test_created_member_cannot_access_admin(auth_client):
    from app.create_member import create_member

    client, _, _, engine = auth_client
    password = secrets.token_urlsafe(24)
    with Session(engine) as session:
        user_id = create_member(session, "new_member", "普通成员", password)
        user = session.get(User, user_id)
        assert user.role == "member"
        assert user.is_active
        assert bcrypt.checkpw(password.encode(), user.password_hash.encode())
        assert user.password_hash != password
        with pytest.raises(ValueError, match="用户名已存在"):
            create_member(session, "new_member", "普通成员", password)
    response = login(client, "new_member", password)
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert client.get("/api/me", headers=header(token)).json()["role"] == "member"
    response = client.get("/api/admin/ping", headers=header(token))
    assert response.status_code == 403
    assert response.json() == {"detail": "需要管理员权限"}
