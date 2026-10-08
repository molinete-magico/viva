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



def _ensure_event_location_nullable() -> None:
    """Compatibilidade para bancos criados antes de atividades deixarem de usar locais."""
    engine = create_engine(settings.database_url)
    try:
        inspector = inspect(engine)
        columns = {column["name"]: column for column in inspector.get_columns("events")}
        location = columns.get("location_id")
        if location is None or location.get("nullable", True):
            return

        if engine.dialect.name == "sqlite":
            with engine.begin() as connection:
                context = MigrationContext.configure(connection)
                operations = Operations(context)
                with operations.batch_alter_table("events", recreate="always") as batch:
                    batch.alter_column(
                        "location_id",
                        existing_type=location["type"],
                        existing_nullable=False,
                        nullable=True,
                    )
        elif engine.dialect.name == "postgresql":
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE events ALTER COLUMN location_id DROP NOT NULL"))
    finally:
        engine.dispose()

def run_migrations() -> None:
    logger.info("running migrations")
    _ensure_event_location_nullable()
    command.upgrade(_alembic_config(), "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
    print("migrations applied")
