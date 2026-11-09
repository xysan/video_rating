import os
from pathlib import Path
import secrets
import subprocess
import sys

import bcrypt
from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]


def test_migration_and_admin_seed(tmp_path):
    password = secrets.token_urlsafe(24)
    env = dict(os.environ, DATABASE_URL="sqlite:///" + (tmp_path / "test.db").as_posix(), SEED_ADMIN_PASSWORD=password)

    def run(*args, success=True, overrides=None):
        result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env | (overrides or {}), capture_output=True)
        assert (result.returncode == 0) == success, result.stderr.decode(errors="replace")
        return result

    run("-m", "alembic", "upgrade", "head")
    engine = create_engine(env["DATABASE_URL"])
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {"users", "video_snapshots", "algorithm_configs", "scores", "alembic_version"}
    assert len(inspector.get_foreign_keys("scores")) == 1
    assert inspector.get_foreign_keys("scores")[0]["referred_table"] == "video_snapshots"
    for table in ("users", "video_snapshots", "algorithm_configs"):
        assert inspector.get_foreign_keys(table) == []
    for table, column in (("scores", "score_detail"), ("video_snapshots", "raw_payload")):
        assert str(next(c["type"] for c in inspector.get_columns(table) if c["name"] == column)) == "JSON"
    run("-m", "app.seed", success=False, overrides={"SEED_ADMIN_PASSWORD": ""})
    run("-m", "app.seed")
    with engine.connect() as conn:
        first_hash = conn.execute(text("SELECT password_hash FROM users WHERE username='admin'")).scalar_one()
    run("-m", "app.seed")
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT username, role, password_hash FROM users")).all()
        assert len(rows) == 1
        assert rows[0][:2] == ("admin", "admin")
        assert rows[0][2] == first_hash
        assert bcrypt.checkpw(password.encode(), first_hash.encode())
        assert password not in first_hash
        for table in ("video_snapshots", "algorithm_configs", "scores"):
            assert conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one() == 0
    engine.dispose()
    run("-m", "alembic", "check")
    run("-m", "alembic", "downgrade", "base")
    with engine.connect() as conn:
        assert set(inspect(conn).get_table_names()) == {"alembic_version"}
    engine.dispose()
    run("-m", "alembic", "upgrade", "head")
