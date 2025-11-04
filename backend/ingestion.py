from typing import Dict, Optional

from flask import Blueprint, jsonify

from .db import SessionLocal
from .helpers import (
    collect_gas_fields,
    collect_meteo_fields,
    extract_station,
    get_payload,
    require_api_key,
    resolve_city,
)
from .models import GasReading, MeteoReading


bp = Blueprint("ingest", __name__)


@bp.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@bp.post("/ingest")
@bp.post("/ingest/<string:path_token>")
def ingest(path_token: Optional[str] = None):
    auth_err = require_api_key(path_token)
    if auth_err:
        return auth_err

    data = get_payload()
    print(f"Data: {data}")
    station = extract_station(data)
    if not station:
        return jsonify({"error": "missing_station_code"}), 400
    city = resolve_city(data, station)

    gas_fields = collect_gas_fields(data)
    meteo_fields = collect_meteo_fields(data)

    has_gas = any(v is not None for v in gas_fields.values())
    has_meteo = any(v is not None for v in meteo_fields.values())
    if not has_gas and not has_meteo:
        return jsonify({"error": "no_metrics"}), 400

    with SessionLocal() as session:
        gas_inserted = 0
        meteo_inserted = 0

        if has_gas:
            _insert_gas(session, station, city, gas_fields)
            gas_inserted = 1

        if has_meteo:
            _insert_meteo(session, station, city, meteo_fields)
            meteo_inserted = 1

        session.commit()

    return jsonify(
        {
            "status": "ok",
            "gas_upserted": gas_inserted,
            "meteo_upserted": meteo_inserted,
        }
    )


def _insert_gas(
    session, station: str, city: Optional[str], fields: Dict[str, Optional[float]]
) -> None:
    payload = {k: v for k, v in fields.items() if v is not None}
    rec = GasReading(station_code=station, city=city, **payload)
    session.add(rec)


def _insert_meteo(
    session, station: str, city: Optional[str], fields: Dict[str, Optional[float]]
) -> None:
    payload = {k: v for k, v in fields.items() if v is not None}
    rec = MeteoReading(station_code=station, city=city, **payload)
    session.add(rec)
