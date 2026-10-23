import hashlib
import hmac
from urllib.parse import urlparse

from aegisops.core.config import get_settings


def generate_csrf_token(session_token: str) -> str:
    """Generates a cryptographically strong, session-bound CSRF token using HMAC-SHA256."""
    settings = get_settings()
    secret = settings.csrf_secret_key.get_secret_value().encode("utf-8")
    return hmac.new(secret, session_token.encode("utf-8"), hashlib.sha256).hexdigest()


def validate_csrf_token(session_token: str, candidate_csrf_token: str | None) -> bool:
    """Validates that a candidate CSRF token matches the session-bound token using constant-time comparison."""
    if not candidate_csrf_token or not session_token:
        return False
    expected_token = generate_csrf_token(session_token)
    return hmac.compare_digest(expected_token, candidate_csrf_token.strip())


def is_allowed_origin(candidate_origin: str | None) -> bool:
    """Validates that an Origin or Referer header matches configured trusted frontend origins."""
    if not candidate_origin:
        return True  # Direct or non-browser client without origin; CSRF token validation still enforced

    settings = get_settings()
    allowed_hosts = set()
    for origin in settings.cors_allowed_origins:
        parsed = urlparse(origin)
        if parsed.netloc:
            allowed_hosts.add(parsed.netloc.lower())

    parsed_candidate = urlparse(candidate_origin)
    candidate_netloc = parsed_candidate.netloc.lower()
    return candidate_netloc in allowed_hosts
