from fastapi import APIRouter

from aegisops.api.approvals import router as approvals_router
from aegisops.api.audit import router as audit_router
from aegisops.api.auth import router as auth_router
from aegisops.api.executions import router as executions_router
from aegisops.api.health import router as health_router
from aegisops.api.incidents import router as incidents_router
from aegisops.api.overview import router as overview_router
from aegisops.api.rollbacks import router as rollbacks_router
from aegisops.api.verifications import router as verifications_router
from aegisops.api.webhooks import router as webhooks_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(overview_router)
api_router.include_router(audit_router)
api_router.include_router(incidents_router)
api_router.include_router(webhooks_router)
api_router.include_router(approvals_router)
api_router.include_router(executions_router)
api_router.include_router(verifications_router)
api_router.include_router(rollbacks_router)
