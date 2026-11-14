"""Prometheus exposition endpoint for BusReserve 2.0."""

from flask import Blueprint, Response

from app.utils.metrics import metrics_registry

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.get("/metrics")
@metrics_bp.get("/api/metrics")
def get_prometheus_metrics() -> Response:
    """Expose application metrics in standard Prometheus text format."""
    payload = metrics_registry.render_prometheus_text()
    return Response(
        payload,
        status=200,
        mimetype="text/plain; version=0.0.4; charset=utf-8",
    )
