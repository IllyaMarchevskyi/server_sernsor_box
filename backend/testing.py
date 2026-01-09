from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from backend.log import log

bp = Blueprint("testing", __name__)


@bp.post("/test")
def test_echo() -> Any:
    server_time = datetime.utcnow().isoformat() + "Z"
    json_body = request.get_json(silent=True)
    data_out: Any = None
    if isinstance(json_body, dict):
        data_out = str(json_body)
    elif request.form:
        data_out = {k: v for k, v in request.form.items()}
    else:
        raw = request.get_data(as_text=True)
        if raw:
            data_out = raw

    if data_out is None:
        log.info("Test echo received empty payload from %s", request.host)
        return jsonify({"error": "empty_payload", "server_time": server_time}), 400

    log.debug("Test echo payload: %s", data_out)
    return jsonify({"data": data_out, "server_time": server_time})


@bp.get("/test")
def test_echo_get() -> Dict[str, Any]:
    server_time = datetime.utcnow().isoformat() + "Z"
    data_out = {k: v for k, v in request.args.items()}
    log.debug("Test echo GET params: %s", data_out)
    return {"data": data_out, "server_time": server_time}
