import sys

import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.database import SessionLocal
from app.models import User


def seed_admin() -> bool:
    password = get_settings().SEED_ADMIN_PASSWORD
    if not password:
        raise ValueError("请先在 backend/.env 设置 SEED_ADMIN_PASSWORD")
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("SEED_ADMIN_PASSWORD 的 UTF-8 编码不能超过 72 字节")
    with SessionLocal() as session:
        if session.scalar(select(User.id).where(User.username == "admin")) is not None:
            return False
        session.add(User(username="admin", password_hash=bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("ascii"), display_name="管理员", role="admin", is_active=True))
        try:
            session.commit()
        except IntegrityError:
            # 并发运行时，唯一约束保证不会重复创建管理员。
            session.rollback()
            if session.scalar(select(User.id).where(User.username == "admin")) is None:
                raise
            return False
    return True


if __name__ == "__main__":
    try:
        created = seed_admin()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    print("管理员已创建" if created else "管理员已存在，未修改密码或角色")
