from typing import Dict, Optional

from flask import Blueprint, jsonify, request
from sqlalchemy import select
from backend.log import log

from .config import CITY_BY_ID
from .db import SessionLocal
from .helpers import (
    collect_gas_fields,
    collect_meteo_fields,
    extract_city_from_payload,
    extract_station,
    get_payload,
    normalize_station_code,
    require_api_key,
    resolve_city,
    transformation_data,
)
from .models import GasReading, MeteoReading, StationMapping

bp = Blueprint("ingest", __name__)


@bp.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@bp.post("/ingest")
@bp.post("/ingest/<string:path_token>")
@bp.post("/ingest/<string:path_token>/<string:city>")
def ingest(path_token: Optional[str] = None, city: Optional[str] = None):
    log.info("Start ingest from %s", request.host)
    auth_err = require_api_key(path_token)
    if auth_err:
        log.warning("Unauthorized ingest attempt from %s", request.host)
        return auth_err

    data = get_payload()
    city_from_path = city
    if city_from_path and "city" not in data and "city_name" not in data:
        data["city"] = city_from_path
    log.debug("Ingest payload: %s", data)
    station = extract_station(data)
    if station:
        station = normalize_station_code(station)
        if not station:
            log.info("Station code normalized to empty")
            return jsonify({"error": "missing_station_code"}), 400

    transformation_data(data)

    gas_fields = collect_gas_fields(data)
    meteo_fields = collect_meteo_fields(data)

    has_gas = any(v is not None for v in gas_fields.values())
    has_meteo = any(v is not None for v in meteo_fields.values())

    with SessionLocal() as session:
        city = city_from_path or resolve_city(session, data, station)

        gas_inserted = 0
        meteo_inserted = 0
        meteo_station = None

        if has_gas:
            if not station:
                log.info("Missing station code for gas payload")
                return jsonify({"error": "missing_station_code"}), 400
            mapping_exists = session.execute(
                select(StationMapping.id).where(
                    StationMapping.station_code == station
                )
            ).scalar_one_or_none()
            if mapping_exists is None:
                session.rollback()
                log.info("Station mapping not found for station=%s", station)
                return (
                    jsonify(
                        {
                            "error": "station_not_registered",
                            "message": "Station code is absent from station_mappings; payload was ignored.",
                        }
                    ),
                    404,
                )
            log.debug("Inserting gas readings for station=%s city=%s", station, city)
            _insert_gas(session, station, city, gas_fields)
            gas_inserted = 1

        if has_meteo:
            if not city:
                log.info("Missing city for meteo payload")
                return jsonify({"error": "missing_city"}), 400
            meteo_station = session.execute(
                select(StationMapping.station_code).where(
                    StationMapping.city == city
                )
            ).scalar_one_or_none()
            if meteo_station is None:
                session.rollback()
                log.info("Station mapping not found for city=%s", city)
                return (
                    jsonify(
                        {
                            "error": "station_not_registered",
                            "message": "City is absent from station_mappings; payload was ignored.",
                        }
                    ),
                    404,
                )
            _insert_meteo(session, meteo_station, city, meteo_fields)
            meteo_inserted = 1

        session.commit()
        station_for_log = station or meteo_station
        log.info(
            "Ingest processed station=%s city=%s gas=%s meteo=%s",
            station_for_log,
            city,
            gas_inserted,
            meteo_inserted,
        )

    return jsonify(
        {
            "status": "ok",
            "gas_upserted": gas_inserted,
            "meteo_upserted": meteo_inserted,
        }
    )


@bp.post("/station-mappings")
@bp.post("/station-mappings/<string:path_token>")
def upsert_station_mapping(path_token: Optional[str] = None):
    auth_err = require_api_key(path_token)
    if auth_err:
        log.warning("Unauthorized station-mapping attempt from %s", request.host)
        return auth_err

    data = get_payload()

    new_code = normalize_station_code(
        data.get("station_code")
    )
    if not new_code:
        log.info("Missing station_code in station-mapping payload")
        return (
            jsonify(
                {
                    "error": "missing_station_code",
                    "message": "Provide station_code (MAC) in the request payload.",
                }
            ),
            400,
        )

    city = extract_city_from_payload(data)
    city_was_provided = any(key in data for key in ("city", "city_name", "city_id"))
    if city is None and city_was_provided:
        log.info("Invalid city provided for station-mapping station=%s", new_code)
        return (
            jsonify(
                {
                    "error": "invalid_city",
                    "message": "Provided city value is not present in CITY_BY_ID.",
                }
            ),
            400,
        )

    previous_code = normalize_station_code(data.get("previous_station_code"))

    with SessionLocal() as session:
        operation = "created"

        existing = None
        if previous_code and previous_code != new_code:
            existing = session.execute(
                select(StationMapping).where(StationMapping.station_code == previous_code)
            ).scalar_one_or_none()
            if existing is None:
                log.info(
                    "Attempt to rename missing station mapping previous=%s",
                    previous_code,
                )
                return (
                    jsonify(
                        {
                            "error": "station_not_found",
                            "message": f"No station mapping found for {previous_code}.",
                        }
                    ),
                    404,
                )
            operation = "renamed"
        elif city:
            existing = session.execute(
                select(StationMapping).where(StationMapping.city == city)
            ).scalar_one_or_none()

        if existing is None:
            existing = session.execute(
                select(StationMapping).where(StationMapping.station_code == new_code)
            ).scalar_one_or_none()

        duplicate = session.execute(
            select(StationMapping).where(StationMapping.station_code == new_code)
        ).scalar_one_or_none()
        if duplicate and (existing is None or duplicate.id != existing.id):
            log.info(
                "Duplicate station code detected new=%s",
                new_code,
            )
            return (
                jsonify(
                    {
                        "error": "duplicate_station_code",
                        "message": f"Station mapping for {new_code} already exists.",
                    }
                ),
                409,
            )

        if existing:
            if city is None:
                city = existing.city
            existing.city = city
            existing.station_code = new_code
            if operation != "renamed":
                operation = "updated"
        else:
            if city is None:
                return (
                    jsonify(
                        {
                            "error": "missing_city",
                            "message": "Provide city/city_name or city_id when creating a new mapping.",
                        }
                    ),
                    400,
                )
            mapping = StationMapping(city=city, station_code=new_code)
            session.add(mapping)
            operation = "created"

        session.commit()
        log.info(
            "Station mapping %s station=%s city=%s",
            operation,
            new_code,
            city,
        )

    return jsonify(
        {
            "status": "ok",
            "station_code": new_code,
            "city": city,
            "operation": operation,
        }
    )


@bp.get("/cities")
@bp.get("/cities/<string:path_token>")
def list_cities(path_token: Optional[str] = None):
    auth_err = require_api_key(path_token)
    if auth_err:
        return auth_err

    cities = [
        {"id": city_id, "name": name} for city_id, name in sorted(CITY_BY_ID.items())
    ]
    return jsonify({"cities": cities})


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
