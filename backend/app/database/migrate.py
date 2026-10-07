import logging

from alembic import command
from alembic.config import Config

from app.config import BACKEND_ROOT, settings

logger = logging.getLogger("viva.migration")


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def run_migrations() -> None:
    logger.info("running migrations")
    command.upgrade(_alembic_config(), "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
    print("migrations applied")
