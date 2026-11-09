import argparse
from getpass import getpass
import sys

import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User


def create_member(session: Session, username: str, display_name: str, password: str) -> int:
    username = username.strip()
    display_name = display_name.strip()
    if not username or len(username) > 191:
        raise ValueError("用户名必须为 1 至 191 个字符")
    if not display_name or len(display_name) > 255:
        raise ValueError("显示名称必须为 1 至 255 个字符")
    encoded = password.encode("utf-8")
    if not encoded or len(encoded) > 72:
        raise ValueError("密码不能为空，UTF-8 编码不能超过 72 字节")
    if session.scalar(select(User.id).where(User.username == username)) is not None:
        raise ValueError("用户名已存在，不会修改已有账号")
    user = User(username=username, display_name=display_name, password_hash=bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("ascii"), role="member", is_active=True)
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("创建失败，请检查用户名是否已存在") from None
    return user.id


def main() -> int:
    parser = argparse.ArgumentParser(description="创建普通成员账号")
    parser.add_argument("username", help="用户名")
    parser.add_argument("--display-name", help="显示名称，默认与用户名相同")
    args = parser.parse_args()
    try:
        # 密码仅通过隐藏输入读取，不接受命令行密码参数。
        password = getpass("密码：")
        if password != getpass("再次输入密码："):
            raise ValueError("两次输入的密码不一致")
        with SessionLocal() as session:
            user_id = create_member(session, args.username, args.display_name or args.username, password)
    except (ValueError, EOFError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"普通成员已创建，ID：{user_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
