from flask import Flask

from .config import Config
from .db import init_db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    from .ingestion import bp as ingest_bp
    from .testing import bp as testing_bp

    app.register_blueprint(ingest_bp)
    app.register_blueprint(testing_bp)

    try:
        init_db()
    except Exception:
        # Database might be unreachable during startup; fail lazily on first request.
        pass

    return app


app = create_app()

