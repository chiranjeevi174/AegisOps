import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from aegisops.api.health import router as health_router
from aegisops.api.router import api_router
from aegisops.core.config import get_settings
from aegisops.core.correlation import (
    generate_request_id,
    sanitize_incoming_id,
    set_request_id,
)
from aegisops.core.logging import configure_logging
from aegisops.observability.metrics import setup_metrics

settings = get_settings()

configure_logging(settings.log_level)

logger = logging.getLogger("aegisops")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting", extra={"event": "app_startup"})
    yield
    logger.info("Application shutting down", extra={"event": "app_shutdown"})


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)


class SecurityHeadersAndCorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Request ID extraction and propagation
        raw_req_id = request.headers.get("x-request-id")
        req_id = sanitize_incoming_id(raw_req_id) or generate_request_id()
        set_request_id(req_id)

        response = await call_next(request)

        # 2. Attach Request ID to response
        response.headers["X-Request-ID"] = req_id

        # 3. Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=()"
        )

        # Prevent browser caching of sensitive API state
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        # HSTS in production HTTPS mode
        if settings.enable_hsts or (
            settings.is_production and request.url.scheme == "https"
        ):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


app.add_middleware(SecurityHeadersAndCorrelationMiddleware)

# CORS configuration restricted to configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
    ],
)

app.include_router(health_router)
app.include_router(api_router)
setup_metrics(app)
