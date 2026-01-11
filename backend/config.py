import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

CITY_BY_CODE: Dict[str, str] = {}

CITY_BY_ID: Dict[int, str] = {
    1: "Pereiaslav",
    2: "Ivankiv",
    3: "Irpin",
    4: "Vyshneve",
    5: "Boyarka",
    6: "Obukhiv",
    7: "Dymerka",
    8: "Kaharlyk",
    9: "Uzyn",
    10: "Boryspil",
    11: "Vyshhorod",
    12: "Vasylkiv",
    13: "Bohuslav",
    14: "Brovary",
    15: "Pidhirtsi",
    16: "Bila_Tserkva",
}


# Attempt to load environment variables from project-level .env file if present.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Config:
    """Application configuration sourced from environment variables."""

    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    DB_HOST: str = os.getenv("DB_HOST", "ecojob.mysql.tools")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "ecojob_test")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "ecojob_test")
    DATABASE_URL2: Optional[str] = os.getenv("DATABASE_URL2")
    DB_HOST2: str = os.getenv("DB_HOST2", "")
    DB_PORT2: int = int(os.getenv("DB_PORT2", "3306"))
    DB_USER2: str = os.getenv("DB_USER2", "")
    DB_PASSWORD2: str = os.getenv("DB_PASSWORD2", "")
    DB_NAME2: str = os.getenv("DB_NAME2", "")
    API_KEY: Optional[str] = os.getenv("INGEST_API_KEY")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


def build_mysql_url_from_parts(
    db_user: str,
    db_password: str,
    db_host: str,
    db_port: int,
    db_name: str,
) -> str:
    return (
        "mysql+mysqlconnector://"
        f"{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        "?charset=utf8mb4"
    )


def build_mysql_url(config: Config = Config) -> str:
    """Construct a SQLAlchemy MySQL connector URL from Config values."""

    return build_mysql_url_from_parts(
        config.DB_USER,
        config.DB_PASSWORD,
        config.DB_HOST,
        config.DB_PORT,
        config.DB_NAME,
    )


def build_mysql_url_secondary(config: Config = Config) -> Optional[str]:
    if not (config.DB_HOST2 and config.DB_USER2 and config.DB_NAME2):
        return None
    return build_mysql_url_from_parts(
        config.DB_USER2,
        config.DB_PASSWORD2,
        config.DB_HOST2,
        config.DB_PORT2,
        config.DB_NAME2,
    )


def log_setup(config: Config = Config):
    LOG_DIR = "logs"
    LOG_FILE = os.path.join(LOG_DIR, "app.log")

    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    file_handler = TimedRotatingFileHandler(
        LOG_FILE, when="midnight", interval=1, backupCount=7, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    console_handler.setLevel(logging.INFO)

    logger = logging.getLogger("APP")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # Мінімальний рівень логування
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
