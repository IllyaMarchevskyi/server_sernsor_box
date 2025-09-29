from typing import Any, Dict, Optional, Tuple

from flask import request

from .config import Config
from .constants import CITY_BY_ID


def require_api_key() -> Optional[Tuple[Dict[str, str], int]]:
    provided = request.headers.get("X-API-Key") or request.args.get("api_key")
    if Config.API_KEY is None:
        return None
    if provided != Config.API_KEY:
        return {"error": "unauthorized"}, 401
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
    return num


def extract_station(data: Dict[str, Any]) -> Optional[str]:
    for key in ["station_code", "station", "name", "device", "device_id", "id"]:
        if key in data and str(data[key]).strip():
            return str(data[key]).strip()
    return None


def _to_city_id(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def resolve_city(data: Dict[str, Any], station: Optional[str]) -> Optional[str]:
    for key in ["city", "city_name"]:
        raw = data.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()

    for key in ["city_id", "station_id", "station_code", "station", "id"]:
        if key in data:
            city_id = _to_city_id(data.get(key))
            if city_id and city_id in CITY_BY_ID:
                return CITY_BY_ID[city_id]

    if station:
        city_id = _to_city_id(station)
        if city_id and city_id in CITY_BY_ID:
            return CITY_BY_ID[city_id]

    return None


def collect_gas_fields(data: Dict[str, Any]) -> Dict[str, Optional[float]]:
    return {
        "co_ppm": to_float(data.get("CO") or data.get("co_ppm")),
        "so2_ppb": to_float(data.get("SO2") or data.get("so2_ppb")),
        "no2_ppb": to_float(data.get("NO2") or data.get("no2_ppb")),
        "no_ppb": to_float(data.get("NO") or data.get("no_ppb")),
        "h2s_ppb": to_float(data.get("H2S") or data.get("h2s_ppb")),
        "o3_ppb": to_float(data.get("O3") or data.get("o3_ppb")),
        "nh3_ppb": to_float(data.get("NH3") or data.get("nh3_ppb")),
        "pm2_5_ugm3": to_float(data.get("PM2.5") or data.get("pm2_5") or data.get("pm2_5_ugm3")),
        "pm10_ugm3": to_float(data.get("PM10") or data.get("pm10") or data.get("pm10_ugm3")),
    }


def collect_meteo_fields(data: Dict[str, Any]) -> Dict[str, Optional[float]]:
    return {
        "wd_deg": to_float(data.get("WD") or data.get("wd_deg")),
        "temp_c": to_float(
            data.get("TEMP")
            or data.get("temp_c")
            or data.get("temperature")
            or data.get("temp")
        ),
        "rh_pct": to_float(
            data.get("RH") or data.get("rh_pct") or data.get("humidity") or data.get("hum")
        ),
        "ws_ms": to_float(
            data.get("WS") or data.get("ws_ms") or data.get("wind") or data.get("wind_speed")
        ),
        "gst_ms": to_float(data.get("GST") or data.get("gst_ms")),
        "rain_mm": to_float(
            data.get("RAIN") or data.get("rain_mm") or data.get("rain") or data.get("rainfall")
        ),
        "uv_index": to_float(data.get("UV") or data.get("uv_index")),
        "lux": to_float(data.get("LUX") or data.get("lux")),
        "pres_hpa": to_float(data.get("PRES") or data.get("pres_hpa") or data.get("pressure")),
    }
