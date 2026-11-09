import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import CurrentUser, LoginRequest
from app.auth.security import verify_password
from app.config import get_settings
from app.database import get_session
from app.models import User

bearer = HTTPBearer(auto_error=False)


def unauthorized(detail: str = "无效或过期的访问令牌") -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def authenticate_user(credentials: LoginRequest, session: Session = Depends(get_session)) -> int:
    user = session.execute(select(User.id, User.password_hash, User.is_active).where(User.username == credentials.username)).mappings().one_or_none()
    valid = verify_password(credentials.password.get_secret_value(), user["password_hash"] if user else None)
    if not valid or user is None or not user["is_active"]:
        raise unauthorized("用户名或密码错误")
    return user["id"]


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), session: Session = Depends(get_session)) -> CurrentUser:
    if credentials is None:
        raise unauthorized()
    try:
        payload = jwt.decode(credentials.credentials, get_settings().JWT_SECRET, algorithms=["HS256"], options={"require": ["sub", "exp", "iat"]})
        subject = payload["sub"]
        if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal() or len(subject) > 10:
            raise ValueError("无效用户标识")
        user_id = int(subject)
        if not 0 < user_id <= 2147483647:
            raise ValueError("用户标识超出范围")
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized() from None
    # 显式选择安全字段，权限每次查询数据库，不信任令牌中的角色。
    user = session.execute(select(User.id, User.username, User.display_name, User.role).where(User.id == user_id, User.is_active.is_(True))).mappings().one_or_none()
    if user is None:
        raise unauthorized()
    return CurrentUser(**user)


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
