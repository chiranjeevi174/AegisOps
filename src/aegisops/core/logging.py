import json
import logging
import re
from datetime import UTC, datetime

from aegisops.core.config import get_settings
from aegisops.core.correlation import (
    get_correlation_id,
    get_execution_id,
    get_incident_id,
    get_request_id,
)

# Common credential patterns to redact
_SENSITIVE_PATTERNS = [
    (
        re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{8,}", re.IGNORECASE),
        r"\1[REDACTED_TOKEN]",
    ),
    (
        re.compile(r"(aegisops_session=)[a-zA-Z0-9_\-\.]{8,}", re.IGNORECASE),
        r"\1[REDACTED_COOKIE]",
    ),
    (
        re.compile(r"(aegisops_csrf=)[a-zA-Z0-9_\-\.]{8,}", re.IGNORECASE),
        r"\1[REDACTED_CSRF]",
    ),
    (re.compile(r"(password=)[^\s&]+", re.IGNORECASE), r"\1[REDACTED_PASSWORD]"),
    (re.compile(r"(api_key=)[^\s&]+", re.IGNORECASE), r"\1[REDACTED_KEY]"),
    (
        re.compile(r"(postgresql\+asyncpg://[^:]+:)[^@]+(@)", re.IGNORECASE),
        r"\1[REDACTED_PASS]\2",
    ),
]


def redact_sensitive_string(text: str) -> str:
    """Redacts known token, cookie, key, and credential patterns from log strings."""
    if not text:
        return text
    sanitized = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        settings = get_settings()

        message = redact_sensitive_string(record.getMessage())

        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "service": "aegisops",
            "environment": settings.environment,
            "logger": record.name,
            "event": getattr(
                record, "event", getattr(record, "event_name", "app_event")
            ),
            "message": message,
        }

        # Request & Workflow Correlation
        req_id = getattr(record, "request_id", None) or get_request_id()
        if req_id:
            payload["request_id"] = req_id

        corr_id = getattr(record, "correlation_id", None) or get_correlation_id()
        if corr_id:
            payload["correlation_id"] = corr_id

        inc_id = getattr(record, "incident_id", None) or get_incident_id()
        if inc_id:
            payload["incident_id"] = str(inc_id)

        exec_id = getattr(record, "execution_id", None) or get_execution_id()
        if exec_id:
            payload["execution_id"] = str(exec_id)

        # Optional structured context
        verification_id = getattr(record, "verification_id", None)
        if verification_id:
            payload["verification_id"] = str(verification_id)

        rollback_assessment_id = getattr(record, "rollback_assessment_id", None)
        if rollback_assessment_id:
            payload["rollback_assessment_id"] = str(rollback_assessment_id)

        error_category = getattr(record, "error_category", None)
        if error_category:
            payload["error_category"] = str(error_category)

        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms

        # Safe exception formatting
        if record.exc_info:
            raw_exc = self.formatException(record.exc_info)
            payload["exception"] = redact_sensitive_string(raw_exc)

        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    logging.basicConfig(
        level=level.upper(),
        handlers=[handler],
        force=True,
    )
