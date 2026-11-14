"""Phase 8 Observability & Logging regression tests."""

from app.utils.logging import SENSITIVE_PATTERNS, sanitize_sensitive_value


def test_metrics_endpoint_returns_prometheus_exposition(client):
    """Verify /metrics and /api/metrics expose standard Prometheus 0.0.4 text."""
    resp_root = client.get("/metrics")
    assert resp_root.status_code == 200
    assert "version=0.0.4" in resp_root.content_type
    body_root = resp_root.data.decode("utf-8")
    assert "busreserve_app_uptime_seconds" in body_root
    assert "busreserve_app_info" in body_root
    assert "busreserve_http_requests_total" in body_root
    assert "busreserve_db_connections" in body_root

    resp_api = client.get("/api/metrics")
    assert resp_api.status_code == 200
    assert "busreserve_app_uptime_seconds" in resp_api.data.decode("utf-8")


def test_http_request_telemetry_increments_on_requests(client):
    """Verify HTTP requests are captured in request counters and latency histograms."""
    # Probe a standard endpoint
    resp = client.get("/health/live")
    assert resp.status_code == 200

    metrics_text = client.get("/metrics").data.decode("utf-8")
    expected_counter = (
        'busreserve_http_requests_total{endpoint="/health/live",method="GET",status_code="200"}'
    )
    expected_histogram = (
        'busreserve_http_request_duration_seconds_count{endpoint="/health/live",method="GET"}'
    )
    assert expected_counter in metrics_text
    assert expected_histogram in metrics_text


def test_sensitive_patterns_include_payment_and_security_fields():
    """Verify payment and security credentials are scrubbed by logging sanitizer."""
    for required in (
        "signature",
        "card",
        "cvv",
        "pan",
        "pin",
        "token",
        "password",
        "secret",
    ):
        assert required in SENSITIVE_PATTERNS

    # Test sanitization function
    raw_payload = {
        "user_email": "passenger@example.com",
        "card_number": "4111222233334444",
        "cvv": "123",
        "gateway_signature": "mock_sig_12345678",
        "nested": {
            "auth_token": "bearer-token-val",
            "pin": "9999",
        },
    }
    sanitized = {k: sanitize_sensitive_value(k, v) for k, v in raw_payload.items()}
    assert sanitized["user_email"] == "passenger@example.com"
    assert sanitized["card_number"] == "[REDACTED]"
    assert sanitized["cvv"] == "[REDACTED]"
    assert sanitized["gateway_signature"] == "[REDACTED]"
    assert sanitized["nested"]["auth_token"] == "[REDACTED]"
    assert sanitized["nested"]["pin"] == "[REDACTED]"
