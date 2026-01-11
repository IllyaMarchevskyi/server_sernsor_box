from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from ..config import Config, build_mysql_url, build_mysql_url_secondary


Base = declarative_base()


def ensure_database_exists(db_url: str) -> None:
    """Best-effort database creation for MySQL backends."""

    url = make_url(db_url)
    backend = url.get_backend_name()
    if not backend.startswith("mysql") or not url.database:
        return

    engine: Optional[Engine] = None
    try:
        engine = create_engine(url.set(database=None), pool_pre_ping=True, future=True)
        db_name = url.database
        with engine.connect() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
            conn.commit()
    except Exception:
        # Ignore failure — table creation will raise later if DB truly absent.
        pass
    finally:
        if engine is not None:
            engine.dispose()


RAW_DB_URL = Config.DATABASE_URL or build_mysql_url()
RAW_DB_URL_SECONDARY = Config.DATABASE_URL2 or build_mysql_url_secondary()

ensure_database_exists(RAW_DB_URL)
if RAW_DB_URL_SECONDARY:
    ensure_database_exists(RAW_DB_URL_SECONDARY)

ENGINE = create_engine(RAW_DB_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)
ENGINE_SECONDARY = (
    create_engine(RAW_DB_URL_SECONDARY, pool_pre_ping=True, future=True)
    if RAW_DB_URL_SECONDARY
    else None
)
SessionLocalSecondary = (
    sessionmaker(bind=ENGINE_SECONDARY, autoflush=False, autocommit=False, future=True)
    if ENGINE_SECONDARY
    else None
)
HAS_SECONDARY = ENGINE_SECONDARY is not None


def init_db() -> None:
    """Create database tables if they do not exist."""

    # Import inside function so models can depend on Base without circular imports.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=ENGINE)
    if ENGINE_SECONDARY is not None:
        Base.metadata.create_all(bind=ENGINE_SECONDARY)
