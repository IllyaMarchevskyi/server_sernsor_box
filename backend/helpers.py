from typing import Any, Dict, Optional, Tuple

from flask import current_app, jsonify, request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Config, CITY_BY_CODE, CITY_BY_ID
from .models import StationMapping


CITY_NAME_LOOKUP = {name.lower(): name for name in CITY_BY_ID.values()}


def require_api_key(path_token: Optional[str] = None) -> Optional[Tuple[Any, int]]:
    provided = (
        request.headers.get("X-API-Key") or request.args.get("api_key") or path_token
    )
    if Config.API_KEY is None:
        return None

    if not provided:
        current_app.logger.warning(
            "Unauthorized ingest request: missing API key",
            extra={
                "remote_addr": request.remote_addr,
                "path": request.path,
            },
        )
        return (
            jsonify(
                {
                    "error": "missing_api_key",
                    "message": "Provide the API key via X-API-Key header, api_key query parameter, or /ingest/<api_key> URL.",
                }
            ),
            401,
        )

    if provided != Config.API_KEY:
        current_app.logger.warning(
            "Unauthorized ingest request: invalid API key",
            extra={
                "remote_addr": request.remote_addr,
                "path": request.path,
            },
        )
        return (
            jsonify(
                {
                    "error": "invalid_api_key",
                    "message": "The supplied API key does not match the INGEST_API_KEY configured on the server.",
                }
            ),
            401,
        )

    return None


def get_payload() -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    json_body = request.get_json(silent=True)
    if isinstance(json_body, dict):
        data = json_body
    elif request.form:
        data = {k: v for k, v in request.form.items()}
    elif request.args:
        data = {k: v for k, v in request.args.items()}
    return data


def to_float(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    if num == -1.0:
        return None
    elif num < 0:
        return 0
    return num


def extract_station(data: Dict[str, Any]) -> Optional[str]:
    for key in ["station_code", "station", "name", "device", "device_id", "id"]:
        if key in data and str(data[key]).strip():
            return str(data[key]).strip()
    return None


def normalize_station_code(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.upper()


def _to_city_id(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _city_from_name(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return CITY_NAME_LOOKUP.get(text.lower())


def extract_city_from_payload(data: Dict[str, Any]) -> Optional[str]:
    for key in ["city", "city_name"]:
        city = _city_from_name(data.get(key))
        if city:
            return city

    for key in ["city_id", "station_id"]:
        city_id = _to_city_id(data.get(key))
        if city_id and city_id in CITY_BY_ID:
            return CITY_BY_ID[city_id]

    return None


def _lookup_city_by_station(
    session: Session, station_code: Optional[str]
) -> Optional[str]:
    code = normalize_station_code(station_code)
    if not code:
        return None

    db_city = session.execute(
        select(StationMapping.city).where(StationMapping.station_code == code)
    ).scalar_one_or_none()
    if db_city:
        return db_city

    return CITY_BY_CODE.get(code)


def resolve_city(
    session: Session, data: Dict[str, Any], station: Optional[str]
) -> Optional[str]:
    city = extract_city_from_payload(data)
    if city:
        return city

    for key in ["station_code", "station", "id"]:
        code_city = _lookup_city_by_station(session, data.get(key))
        if code_city:
            return code_city

    if station:
        city_from_station = _lookup_city_by_station(session, station)
        if city_from_station:
            return city_from_station

        numeric_station = _to_city_id(station)
        if numeric_station and numeric_station in CITY_BY_ID:
            return CITY_BY_ID[numeric_station]

    return None


def transformation_data(data: Dict[str, Any]):
    for key in data.keys():
        if key == "tempinf":
            data[key] = (to_float(data[key]) - 32) * 5 / 9
            continue
        data[key] = to_float(data[key])


def collect_gas_fields(data: Dict[str, Any]) -> Dict[str, Optional[float]]:
    return {
        "CO": data.get("CO"),
        "SO2": data.get("SO2"),
        "NO2": data.get("NO2"),
        "NO": data.get("NO"),
        "H2S": data.get("H2S"),
        "O3": data.get("O3"),
        "NH3": data.get("NH3"),
        "PM2_5": data.get("PM2.5"),
        "PM10": data.get("PM10"),
        "R": data.get("R"),
    }


def collect_meteo_fields(data: Dict[str, Any]) -> Dict[str, Optional[float]]:
    return {
        "P": data.get("WD") or data.get("wd_deg"),
        "TEMP": data.get("tempinf"),
        "RH": data.get("humidityin"),
    }
