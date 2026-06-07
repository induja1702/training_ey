# app/__init__.py
from flask              import Flask, g, request, jsonify
from app.handlers.logging_config import configure_logging, logger
from app.routers.predictions import bp
import structlog, time, uuid

def create_app(config: dict | None = None) -> Flask:
    configure_logging()
    app = Flask(__name__)
    app.config["TESTING"] = False
    if config:
        app.config.update(config)

    # ── Register Blueprint ────────────────────────────────────────────────────
    app.register_blueprint(bp)

    # ── Request middleware: inject correlation_id + start timer ──────────────
    @app.before_request
    def before():
        g.start_time     = time.perf_counter()
        g.correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id = g.correlation_id,
            method         = request.method,
            path           = request.path,
        )

    @app.after_request
    def after(response):
        duration_ms = round((time.perf_counter() - g.start_time) * 1000, 2)
        logger.info("request_complete",
                    status      = response.status_code,
                    duration_ms = duration_ms)
        response.headers["X-Correlation-ID"] = g.correlation_id
        return response

    # ── Error handlers ────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        logger.warning("http_404", detail=str(e))
        return jsonify({"error": "Not Found", "message": str(e)}), 404

    @app.errorhandler(422)
    def unprocessable(e):
        logger.warning("http_422", detail=str(e))
        return jsonify({"error": "Unprocessable Entity", "message": str(e)}), 422

    @app.errorhandler(500)
    def server_error(e):
        logger.error("http_500", detail=str(e))
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

    return app
