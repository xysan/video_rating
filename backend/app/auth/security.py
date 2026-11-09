from datetime import datetime, timedelta, timezone
import secrets

import bcrypt
import jwt

from app.config import get_settings

# 未知用户也执行 bcrypt 校验，降低根据耗时枚举用户名的风险。
DUMMY_PASSWORD_HASH = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt())


def verify_password(password: str, password_hash: str | None) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        bcrypt.checkpw(b"", DUMMY_PASSWORD_HASH)
        return False
    try:
        valid = bcrypt.checkpw(encoded, password_hash.encode("ascii") if password_hash else DUMMY_PASSWORD_HASH)
    except (ValueError, UnicodeError):
        return False
    return valid and password_hash is not None


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
