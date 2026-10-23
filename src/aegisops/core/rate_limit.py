"""Targeted API Rate Limiting for AegisOps (Step 16).

Implements a thread-safe sliding-window rate limiter with:
- Endpoint-specific limits (auth, webhook, AI analysis, decisions, execution).
- Trusted proxy awareness for secure client IP extraction.
- Standard HTTP 429 Too Many Requests responses with Retry-After and X-RateLimit headers.
- Clean separation from secrets (never puts tokens or credentials in keys).
- Architectural note: Process-local in-memory implementation. Distributed deployments
  require Redis or an API gateway.
"""

import math
import threading
import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from aegisops.core.config import get_settings


def get_client_ip(request: Request) -> str:
    """Extracts client IP address safely, respecting trusted proxy configuration."""
    settings = get_settings()
    peer_ip = request.client.host if request.client else "unknown"

    # Only trust X-Forwarded-For if direct peer is an approved trusted proxy
    if peer_ip in settings.trusted_proxies:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Use the first IP in the chain before proxy
            parts = [p.strip() for p in forwarded.split(",")]
            if parts and parts[0]:
                return parts[0]

    return peer_ip


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window in-memory rate limiter.

    Note: In-memory counters are per-process. For distributed horizontal production
    deployments, configure an external shared cache (e.g. Redis) or ingress rate limiter.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int]:
        """Checks if a request is permitted under the rate limit.

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        now = time.monotonic()
        window_start = now - window_seconds

        with self._lock:
            history = self._hits[key]
            # Prune events older than sliding window
            self._hits[key] = [t for t in history if t > window_start]
            valid_history = self._hits[key]

            if len(valid_history) >= max_requests:
                oldest_hit = valid_history[0]
                retry_after = max(1, math.ceil(oldest_hit + window_seconds - now))
                return False, 0, retry_after

            valid_history.append(now)
            remaining = max(0, max_requests - len(valid_history))
            return True, remaining, 0

    def reset(self) -> None:
        """Clears all rate limit state (useful in test suites)."""
        with self._lock:
            self._hits.clear()


GLOBAL_RATE_LIMITER = SlidingWindowRateLimiter()


def rate_limiter(
    endpoint_category: str,
    limit_getter: Callable[[], int],
    window_seconds: int = 60,
):
    """FastAPI dependency factory enforcing targeted rate limits per endpoint category."""

    async def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return

        max_requests = limit_getter()
        client_ip = get_client_ip(request)
        rate_key = f"{endpoint_category}:{client_ip}"

        allowed, _remaining, retry_after = GLOBAL_RATE_LIMITER.check_rate_limit(
            key=rate_key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        if not allowed:
            # Increment security denial metric if available
            try:
                from aegisops.observability.metrics import SECURITY_DENIALS

                SECURITY_DENIALS.labels(
                    reason="rate_limited",
                    endpoint=endpoint_category,
                ).inc()
            except (ImportError, AttributeError):
                pass

            headers = {
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(retry_after),
            }
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {endpoint_category}. Please retry after {retry_after} seconds.",
                headers=headers,
            )

    return dependency


# Standardized dependency instances for sensitive endpoints
rate_limit_auth = rate_limiter(
    "auth",
    lambda: get_settings().rate_limit_auth_per_minute,
)

rate_limit_webhook = rate_limiter(
    "webhook",
    lambda: get_settings().rate_limit_webhook_per_minute,
)

rate_limit_analysis = rate_limiter(
    "incident_analysis",
    lambda: get_settings().rate_limit_analysis_per_minute,
)

rate_limit_decisions = rate_limiter(
    "approval_decision",
    lambda: get_settings().rate_limit_decisions_per_minute,
)

rate_limit_executions = rate_limiter(
    "execution",
    lambda: get_settings().rate_limit_executions_per_minute,
)

rate_limit_verifications = rate_limiter(
    "verification",
    lambda: get_settings().rate_limit_executions_per_minute,
)

rate_limit_rollbacks = rate_limiter(
    "rollback_assessment",
    lambda: get_settings().rate_limit_executions_per_minute,
)
