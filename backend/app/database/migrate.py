import logging

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from alembic import command
from alembic.config import Config

from app.config import BACKEND_ROOT, settings

logger = logging.getLogger("viva.migration")


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def _ensure_events_nullable() -> None:
    """Compatibilidade para bancos antigos enquanto atividades deixam de usar agenda/local."""
    engine = create_engine(settings.database_url)
    try:
        inspector = inspect(engine)
        if "events" not in inspector.get_table_names():
            return
        columns = {column["name"]: column for column in inspector.get_columns("events")}
        nullable_columns = [
            name for name in ("location_id", "scheduled_at")
            if name in columns and not columns[name].get("nullable", True)
        ]
        if not nullable_columns:
            return

        if engine.dialect.name == "sqlite":
            with engine.begin() as connection:
                context = MigrationContext.configure(connection)
                operations = Operations(context)
                with operations.batch_alter_table("events", recreate="always") as batch:
                    for name in nullable_columns:
                        batch.alter_column(
                            name,
                            existing_type=columns[name]["type"],
                            existing_nullable=False,
                            nullable=True,
                        )
        elif engine.dialect.name == "postgresql":
            with engine.begin() as connection:
                for name in nullable_columns:
                    connection.execute(text(f'ALTER TABLE events ALTER COLUMN "{name}" DROP NOT NULL'))
    finally:
        engine.dispose()


def run_migrations() -> None:
    logger.info("running migrations")
    _ensure_events_nullable()
    command.upgrade(_alembic_config(), "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
    print("migrations applied")
