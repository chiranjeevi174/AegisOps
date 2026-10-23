"""Request and workflow correlation tracking for AegisOps (Step 16).

Maintains asynchronous context variables for request correlation across HTTP calls,
background workflows, database transactions, and structured logging.
"""

import re
import uuid
from contextvars import ContextVar

_REQUEST_ID_VAR: ContextVar[str] = ContextVar("request_id", default="")
_CORRELATION_ID_VAR: ContextVar[str] = ContextVar("correlation_id", default="")
_INCIDENT_ID_VAR: ContextVar[str] = ContextVar("incident_id", default="")
_EXECUTION_ID_VAR: ContextVar[str] = ContextVar("execution_id", default="")

_SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{1,64}$")


def sanitize_incoming_id(raw_id: str | None) -> str | None:
    """Validates and bounds client-provided correlation identifiers to prevent log pollution."""
    if not raw_id:
        return None
    cleaned = raw_id.strip()
    if _SAFE_ID_REGEX.match(cleaned):
        return cleaned
    return None


def generate_request_id() -> str:
    """Generates a UUID4-based standard request identifier."""
    return f"req_{uuid.uuid4().hex[:16]}"


def get_request_id() -> str:
    return _REQUEST_ID_VAR.get() or ""


def set_request_id(req_id: str) -> None:
    _REQUEST_ID_VAR.set(req_id)


def get_correlation_id() -> str:
    return _CORRELATION_ID_VAR.get() or ""


def set_correlation_id(corr_id: str) -> None:
    _CORRELATION_ID_VAR.set(corr_id)


def get_incident_id() -> str:
    return _INCIDENT_ID_VAR.get() or ""


def set_incident_id(inc_id: str) -> None:
    _INCIDENT_ID_VAR.set(inc_id)


def get_execution_id() -> str:
    return _EXECUTION_ID_VAR.get() or ""


def set_execution_id(exec_id: str) -> None:
    _EXECUTION_ID_VAR.set(exec_id)
