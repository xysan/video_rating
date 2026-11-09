from alembic import context
from sqlalchemy import create_engine, pool

from app.config import get_settings
from app.models import Base


def run_migrations_offline():
    context.configure(url=get_settings().DATABASE_URL, target_metadata=Base.metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = create_engine(get_settings().DATABASE_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
