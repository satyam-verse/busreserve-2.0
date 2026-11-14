"""Thread-safe Prometheus metrics collector and exposition generator for BusReserve 2.0.

Provides standard Prometheus text exposition format (version 0.0.4) without external dependencies.
"""

import os
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from flask import Flask, Response, request


class MetricRegistry:
    """Thread-safe registry for Prometheus counters, gauges, and histograms."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self.counter_help: dict[str, str] = {}

        self.gauges: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self.gauge_callbacks: dict[
            str, tuple[str, Callable[[], list[tuple[dict[str, str], float]]]]
        ] = {}
        self.gauge_help: dict[str, str] = {}

        self.histograms: dict[str, dict[str, Any]] = {}
        self.histogram_help: dict[str, str] = {}
        self.start_time = time.time()

    def register_counter(self, name: str, help_text: str) -> None:
        with self._lock:
            self.counter_help[name] = help_text

    def inc_counter(
        self, name: str, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        label_tuple = tuple(sorted(labels.items())) if labels else ()
        with self._lock:
            self.counters[name][label_tuple] += value

    def register_gauge(self, name: str, help_text: str) -> None:
        with self._lock:
            self.gauge_help[name] = help_text

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        label_tuple = tuple(sorted(labels.items())) if labels else ()
        with self._lock:
            self.gauges[name][label_tuple] = value

    def register_gauge_callback(
        self,
        name: str,
        help_text: str,
        callback: Callable[[], list[tuple[dict[str, str], float]]],
    ) -> None:
        with self._lock:
            self.gauge_callbacks[name] = (help_text, callback)

    def register_histogram(
        self, name: str, help_text: str, buckets: list[float] | None = None
    ) -> None:
        default_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        configured_buckets = sorted(buckets or default_buckets)
        with self._lock:
            self.histogram_help[name] = help_text
            self.histograms[name] = {
                "buckets": configured_buckets,
                "data": defaultdict(
                    lambda: {
                        "count": 0,
                        "sum": 0.0,
                        "bucket_counts": [0] * len(configured_buckets),
                    }
                ),
            }

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        label_tuple = tuple(sorted(labels.items())) if labels else ()
        with self._lock:
            if name not in self.histograms:
                return
            hist_cfg = self.histograms[name]
            buckets = hist_cfg["buckets"]
            entry = hist_cfg["data"][label_tuple]
            entry["count"] += 1
            entry["sum"] += value
            for i, bound in enumerate(buckets):
                if value <= bound:
                    entry["bucket_counts"][i] += 1

    def _format_labels(self, label_tuple: tuple[tuple[str, str], ...]) -> str:
        if not label_tuple:
            return ""
        pairs = [f'{k}="{v}"' for k, v in label_tuple]
        return "{" + ",".join(pairs) + "}"

    def render_prometheus_text(self) -> str:
        """Render metrics into Prometheus text exposition format (version 0.0.4)."""
        lines: list[str] = []

        # Application metadata & uptime
        uptime = round(time.time() - self.start_time, 2)
        lines.append(
            "# HELP busreserve_app_uptime_seconds Total runtime of BusReserve backend process"
        )
        lines.append("# TYPE busreserve_app_uptime_seconds gauge")
        lines.append(f"busreserve_app_uptime_seconds {uptime}")

        lines.append("# HELP busreserve_app_info BusReserve build and runtime metadata")
        lines.append("# TYPE busreserve_app_info gauge")
        env_mode = os.getenv("FLASK_ENV", "production")
        lines.append(
            f'busreserve_app_info{{version="2.0.0",environment="{env_mode}",python="3.12"}} 1'
        )

        # Static Gauges
        with self._lock:
            for name, help_text in sorted(self.gauge_help.items()):
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} gauge")
                for label_tuple, val in sorted(self.gauges[name].items()):
                    lbl_str = self._format_labels(label_tuple)
                    lines.append(f"{name}{lbl_str} {val}")

            # Dynamic Callback Gauges
            for name, (help_text, cb) in sorted(self.gauge_callbacks.items()):
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} gauge")
                try:
                    results = cb()
                    for labels, val in results:
                        lbl_tuple = tuple(sorted(labels.items())) if labels else ()
                        lbl_str = self._format_labels(lbl_tuple)
                        lines.append(f"{name}{lbl_str} {val}")
                except Exception:
                    lines.append(f"{name} 0")

            # Counters
            for name, help_text in sorted(self.counter_help.items()):
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} counter")
                for label_tuple, val in sorted(self.counters[name].items()):
                    lbl_str = self._format_labels(label_tuple)
                    lines.append(f"{name}{lbl_str} {val}")

            # Histograms
            for name, help_text in sorted(self.histogram_help.items()):
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} histogram")
                hist_cfg = self.histograms[name]
                buckets = hist_cfg["buckets"]
                for label_tuple, data in sorted(hist_cfg["data"].items()):
                    base_labels = dict(label_tuple)
                    # Cumulative buckets
                    cumulative = 0
                    for bound, count in zip(buckets, data["bucket_counts"], strict=False):
                        cumulative += count
                        b_labels = dict(base_labels)
                        b_labels["le"] = str(bound)
                        lbl_str = self._format_labels(tuple(sorted(b_labels.items())))
                        lines.append(f"{name}_bucket{lbl_str} {cumulative}")
                    # +Inf bucket
                    inf_labels = dict(base_labels)
                    inf_labels["le"] = "+Inf"
                    inf_lbl_str = self._format_labels(tuple(sorted(inf_labels.items())))
                    lines.append(f"{name}_bucket{inf_lbl_str} {data['count']}")
                    # Sum and Count
                    lines.append(f"{name}_sum{self._format_labels(label_tuple)} {data['sum']:.6f}")
                    lines.append(f"{name}_count{self._format_labels(label_tuple)} {data['count']}")

        return "\n".join(lines) + "\n"


# Global singleton metrics registry
metrics_registry = MetricRegistry()

# Register core application metrics
metrics_registry.register_counter(
    "busreserve_http_requests_total", "Total HTTP requests processed by BusReserve API"
)
metrics_registry.register_histogram(
    "busreserve_http_request_duration_seconds",
    "HTTP request latency histogram in seconds",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
metrics_registry.register_counter(
    "busreserve_bookings_created_total", "Total seat reservations created"
)
metrics_registry.register_counter(
    "busreserve_payment_transactions_total", "Total payment transactions processed"
)
metrics_registry.register_counter(
    "busreserve_payment_amount_inr_total", "Total transaction amount processed in INR"
)
metrics_registry.register_counter(
    "busreserve_notifications_dispatched_total", "Total notifications recorded and sent"
)
metrics_registry.register_counter(
    "busreserve_ai_requests_total", "Total AI assistant queries handled"
)


def register_database_metrics(app: Flask) -> None:
    """Register dynamic connection pool gauges that inspect the active SQLAlchemy pool."""

    def _get_pool_status():
        try:
            with app.app_context():
                from app.extensions import db

                pool = db.engine.pool
                return [
                    ({"metric": "checked_out"}, float(pool.checkedout())),
                    ({"metric": "checked_in"}, float(pool.checkedin())),
                    ({"metric": "size"}, float(pool.size())),
                    ({"metric": "overflow"}, float(pool.overflow())),
                ]
        except Exception:
            return [
                ({"metric": "checked_out"}, 0.0),
                ({"metric": "checked_in"}, 0.0),
                ({"metric": "size"}, 0.0),
                ({"metric": "overflow"}, 0.0),
            ]

    metrics_registry.register_gauge_callback(
        "busreserve_db_connections",
        "PostgreSQL connection pool utilization status",
        _get_pool_status,
    )


def init_metrics_middleware(app: Flask) -> None:
    """Initialize request-latency and throughput telemetry hooks."""
    register_database_metrics(app)

    @app.before_request
    def _metrics_start_timer() -> None:
        request._busreserve_metric_start = time.perf_counter()

    @app.after_request
    def _metrics_record_request(response: Response) -> Response:
        start_time = getattr(request, "_busreserve_metric_start", None)
        if start_time is not None:
            duration = max(0.0, time.perf_counter() - start_time)
            endpoint = request.url_rule.rule if request.url_rule else request.path
            # Do not record high volume on /metrics itself to avoid self-amplification
            if endpoint not in ("/metrics", "/api/metrics"):
                labels = {
                    "method": request.method,
                    "endpoint": endpoint,
                    "status_code": str(response.status_code),
                }
                metrics_registry.inc_counter("busreserve_http_requests_total", 1.0, labels)
                metrics_registry.observe_histogram(
                    "busreserve_http_request_duration_seconds",
                    duration,
                    {"method": request.method, "endpoint": endpoint},
                )
        return response
