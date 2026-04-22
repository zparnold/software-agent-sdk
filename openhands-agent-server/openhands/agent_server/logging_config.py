"""Custom logging configuration for uvicorn to reuse the SDK's root logger."""

import logging
from typing import Any

from pythonjsonlogger.json import JsonFormatter

from openhands.sdk.logger import ENV_JSON, ENV_LOG_LEVEL, IN_CI


# Paths that produce high-volume, low-signal access log entries (e.g. k8s
# liveness probes hitting /alive every few seconds). Dropping these at the
# log-filter level keeps all other access logs — including non-2xx responses
# on the same paths — intact; see HealthCheckAccessLogFilter below.
_HEALTH_CHECK_PATHS = frozenset({"/alive"})


class HealthCheckAccessLogFilter(logging.Filter):
    """Drop successful uvicorn access log records for health-check endpoints.

    Uvicorn emits access log records with ``record.args`` as a 5-tuple of
    ``(client_addr, method, full_path, http_version, status_code)``. When the
    path is a known health-check endpoint AND the response is 2xx, we drop
    the record. Non-2xx responses (probe failures) still pass through so
    operators can see real liveness issues.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not isinstance(args, tuple) or len(args) < 5:
            return True
        full_path = args[2]
        status_code = args[4]
        if not isinstance(full_path, str):
            return True
        # Strip query string so ``/alive?foo=1`` is still matched.
        path = full_path.split("?", 1)[0]
        if path not in _HEALTH_CHECK_PATHS:
            return True
        try:
            code = int(status_code)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return True
        # Only suppress successful probes; surface failures.
        return not (200 <= code < 300)


class UvicornAccessJsonFormatter(JsonFormatter):
    """JSON formatter for uvicorn access logs that extracts HTTP fields.

    Uvicorn access logs pass structured data in record.args as a tuple:
    (client_addr, method, full_path, http_version, status_code)

    This formatter extracts these into separate JSON fields for better
    querying and analysis in log aggregation systems like Datadog.
    """

    def add_fields(
        self,
        log_data: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_data, record, message_dict)

        # Extract HTTP fields from uvicorn access log args
        # record.args is a tuple for uvicorn access logs:
        # (client_addr, method, full_path, http_version, status_code)
        args = record.args
        if isinstance(args, tuple) and len(args) >= 5:
            client_addr, method, full_path, http_version, status_code = args[:5]
            log_data["http.client_ip"] = client_addr
            log_data["http.method"] = method
            log_data["http.url"] = full_path
            log_data["http.version"] = http_version
            # status_code from uvicorn is typically an int, but handle edge cases
            if isinstance(status_code, int):
                log_data["http.status_code"] = status_code
            elif isinstance(status_code, str) and status_code.isdigit():
                log_data["http.status_code"] = int(status_code)
            else:
                log_data["http.status_code"] = status_code


def get_uvicorn_logging_config() -> dict[str, Any]:
    """
    Generate uvicorn logging configuration that integrates with SDK's root logger.

    This function creates a logging configuration that:
    1. Preserves the SDK's root logger configuration
    2. Routes uvicorn logs through the same handlers
    3. Uses JSON formatter for access logs when LOG_JSON=true or in CI
    4. Extracts HTTP fields into structured JSON attributes
    """
    use_json = ENV_JSON or IN_CI
    log_level = logging.getLevelName(ENV_LOG_LEVEL)

    # Base configuration
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "incremental": False,
        "filters": {
            # Drops successful (2xx) access-log records for /alive probes so
            # k8s liveness-check traffic does not spam the access log.
            "health_check_access": {
                "()": HealthCheckAccessLogFilter,
            },
        },
        "formatters": {},
        "handlers": {},
        "loggers": {
            # Common logger configurations - propagate to root
            "uvicorn": {
                "handlers": [],
                "level": log_level,
                "propagate": True,
            },
            "uvicorn.error": {
                "handlers": [],
                "level": log_level,
                "propagate": True,
            },
        },
    }

    if use_json:
        # Define JSON formatter for access logs with HTTP field extraction
        config["formatters"]["access_json"] = {
            "()": UvicornAccessJsonFormatter,
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }

        # Define handler for access logs
        config["handlers"]["access_json"] = {
            "class": "logging.StreamHandler",
            "formatter": "access_json",
            "stream": "ext://sys.stderr",
        }

        # Access logger uses dedicated JSON handler with HTTP field extraction
        config["loggers"]["uvicorn.access"] = {
            "handlers": ["access_json"],
            "level": log_level,
            "propagate": False,  # Don't double-log
            "filters": ["health_check_access"],
        }
    else:
        # Non-JSON mode: propagate access logs to root (uses Rich handler)
        config["loggers"]["uvicorn.access"] = {
            "handlers": [],
            "level": log_level,
            "propagate": True,
            "filters": ["health_check_access"],
        }

    return config


LOGGING_CONFIG = get_uvicorn_logging_config()
