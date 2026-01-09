from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import BigInteger, Column, DateTime, Index, Numeric, String

from .db import Base


def _kyiv_now() -> datetime:
    """Return naive datetime representing current time in Kyiv."""

    return datetime.now(ZoneInfo("Europe/Kyiv")).replace(tzinfo=None)


class GasReading(Base):
    __tablename__ = "gas_readings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    station_code = Column(String(64), nullable=False)
    city = Column(String(64), nullable=True)
    time = Column(DateTime, nullable=False, default=_kyiv_now)

    co_mg_m3 = Column(Numeric(10, 4))
    so2_mg_m3 = Column(Numeric(10, 4))
    no2_mg_m3 = Column(Numeric(10, 4))
    no_mg_m3 = Column(Numeric(10, 4))
    h2s_mg_m3 = Column(Numeric(10, 4))
    o3_mg_m3 = Column(Numeric(10, 4))
    nh3_mg_m3 = Column(Numeric(10, 4))
    pm2_5_mg_m3 = Column(Numeric(10, 4))
    pm10_mg_m3 = Column(Numeric(10, 4))

    __table_args__ = (
        Index("ix_gas_station_time", "station_code", "time"),
        Index("ix_gas_time", "time"),
        Index("ix_gas_city", "city"),
    )


class MeteoReading(Base):
    __tablename__ = "env_readings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    station_code = Column(String(64), nullable=False)
    city = Column(String(64), nullable=True)
    time = Column(DateTime, nullable=False, default=_kyiv_now)

    wd_deg = Column(Numeric(10, 4))
    temp_c = Column(Numeric(10, 4))
    rh_pct = Column(Numeric(10, 4))
    R_µsv = Column(Numeric(10, 4))

    __table_args__ = (
        Index("ix_meteo_station_time", "station_code", "time"),
        Index("ix_meteo_time", "time"),
        Index("ix_meteo_city", "city"),
    )


class StationMapping(Base):
    __tablename__ = "station_mappings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    station_code = Column(String(64), nullable=False, unique=True)
    city = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=_kyiv_now)
    updated_at = Column(DateTime, nullable=False, default=_kyiv_now, onupdate=_kyiv_now)

    __table_args__ = (
        Index("ix_station_mapping_code", "station_code"),
        Index("ix_station_mapping_city", "city"),
    )
