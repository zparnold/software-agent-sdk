"""Tests for uvicorn logging configuration, especially the access-log filter
that silences successful /alive liveness-probe noise."""

import logging

from openhands.agent_server.logging_config import (
    HealthCheckAccessLogFilter,
    get_uvicorn_logging_config,
)


def _make_access_record(
    full_path: str, status_code: object, *, method: str = "GET"
) -> logging.LogRecord:
    """Build a LogRecord shaped like uvicorn.access emits."""
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("10.0.0.1:1234", method, full_path, "1.1", status_code),
        exc_info=None,
    )
    return record


class TestHealthCheckAccessLogFilter:
    def test_drops_alive_200(self) -> None:
        f = HealthCheckAccessLogFilter()
        assert f.filter(_make_access_record("/alive", 200)) is False

    def test_drops_alive_204(self) -> None:
        f = HealthCheckAccessLogFilter()
        assert f.filter(_make_access_record("/alive", 204)) is False

    def test_drops_alive_with_query_string(self) -> None:
        f = HealthCheckAccessLogFilter()
        assert f.filter(_make_access_record("/alive?verbose=1", 200)) is False

    def test_keeps_alive_non_2xx(self) -> None:
        """Probe failures should still be visible."""
        f = HealthCheckAccessLogFilter()
        assert f.filter(_make_access_record("/alive", 500)) is True
        assert f.filter(_make_access_record("/alive", 503)) is True
        assert f.filter(_make_access_record("/alive", 404)) is True

    def test_keeps_other_health_endpoints(self) -> None:
        """Only /alive is silenced; /health and /ready pass through."""
        f = HealthCheckAccessLogFilter()
        assert f.filter(_make_access_record("/health", 200)) is True
        assert f.filter(_make_access_record("/ready", 200)) is True

    def test_keeps_non_health_paths(self) -> None:
        f = HealthCheckAccessLogFilter()
        assert f.filter(_make_access_record("/api/v1/conversations", 200)) is True
        assert f.filter(_make_access_record("/", 200)) is True

    def test_keeps_records_with_unexpected_args(self) -> None:
        """Guard: if args is not the expected 5-tuple, don't drop the record."""
        f = HealthCheckAccessLogFilter()
        record = logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="unexpected format",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is True

    def test_keeps_records_with_non_int_status(self) -> None:
        """Guard: malformed status codes should not cause records to drop."""
        f = HealthCheckAccessLogFilter()
        assert f.filter(_make_access_record("/alive", "not-a-status")) is True


class TestLoggingConfigWiresFilter:
    def test_filter_registered_on_uvicorn_access(self) -> None:
        config = get_uvicorn_logging_config()
        assert "health_check_access" in config["filters"]
        access_logger = config["loggers"]["uvicorn.access"]
        assert "health_check_access" in access_logger["filters"]
