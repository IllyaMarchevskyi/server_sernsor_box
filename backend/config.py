import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


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
    API_KEY: Optional[str] = os.getenv("INGEST_API_KEY")


def build_mysql_url(config: Config = Config) -> str:
    """Construct a SQLAlchemy MySQL connector URL from Config values."""

    return (
        "mysql+mysqlconnector://"
        f"{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
        "?charset=utf8mb4"
    )
