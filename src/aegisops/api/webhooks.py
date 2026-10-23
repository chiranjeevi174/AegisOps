from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.api.webhook_schemas import AlertmanagerPayload
from aegisops.core.rate_limit import rate_limit_webhook
from aegisops.core.webhook_auth import verify_webhook_token
from aegisops.db.session import get_db
from aegisops.observability.metrics import INCIDENT_INGESTION
from aegisops.services.alert_ingestion import process_alerts

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/alertmanager",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_webhook_token), Depends(rate_limit_webhook)],
)
async def receive_alertmanager_webhook(
    payload: AlertmanagerPayload,
    db: DbSession,
):
    result = await process_alerts(db, payload)

    # Record Prometheus ingestion metrics with low-cardinality labels
    for alert in payload.alerts:
        sev = str(alert.labels.get("severity", "unknown")).lower()
        INCIDENT_INGESTION.labels(source="alertmanager", severity=sev).inc()

    return {
        "status": "processed",
        **result,
    }
