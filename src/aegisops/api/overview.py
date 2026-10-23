from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.core.auth import AuthenticatedActor, get_current_actor
from aegisops.core.config import get_settings
from aegisops.db.session import get_db
from aegisops.domain.approval import ApprovalStatus, RemediationApproval
from aegisops.domain.execution import RemediationExecution
from aegisops.domain.incident import Incident
from aegisops.domain.rollback import RollbackAssessment
from aegisops.domain.verification import ExecutionVerification
from aegisops.integrations.prometheus import (
    QUERIES,
    PrometheusError,
    query_prometheus,
    query_prometheus_range,
)

router = APIRouter(tags=["Overview & System"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


class SystemOverviewResponse(BaseModel):
    total_incidents: int
    open_incidents: int
    incidents_by_severity: dict[str, int]
    incidents_by_status: dict[str, int]
    pending_approvals: int
    total_approvals: int
    total_executions: int
    executions_by_status: dict[str, int]
    executions_by_mode: dict[str, int]
    total_verifications: int
    verifications_by_outcome: dict[str, int]
    total_rollback_assessments: int
    rollback_by_readiness: dict[str, int]
    service_availability: float | None
    service_up: bool | None
    monitoring_available: bool
    grafana_url: str
    incident_creation_trend: list[dict[str, Any]]


class TelemetryPoint(BaseModel):
    timestamp: str
    value: float


class SystemSettingsResponse(BaseModel):
    app_name: str
    environment: str
    version: str
    live_diagnostics_enabled: bool
    prometheus_url: str
    grafana_url: str
    monitoring_available: bool
    current_actor: dict[str, Any]


@router.get("/overview", response_model=SystemOverviewResponse)
async def get_system_overview(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
):
    # Incidents statistics
    total_incidents_stmt = select(func.count(Incident.id))
    total_incidents = await db.scalar(total_incidents_stmt) or 0

    open_incidents_stmt = select(func.count(Incident.id)).where(
        Incident.status == "open"
    )
    open_incidents = await db.scalar(open_incidents_stmt) or 0

    severity_stmt = select(Incident.severity, func.count(Incident.id)).group_by(
        Incident.severity
    )
    severity_res = await db.execute(severity_stmt)
    incidents_by_severity = {row[0]: row[1] for row in severity_res.all()}

    status_stmt = select(Incident.status, func.count(Incident.id)).group_by(
        Incident.status
    )
    status_res = await db.execute(status_stmt)
    incidents_by_status = {row[0]: row[1] for row in status_res.all()}

    # Approvals statistics
    pending_approvals_stmt = select(func.count(RemediationApproval.id)).where(
        RemediationApproval.status == ApprovalStatus.PENDING.value
    )
    pending_approvals = await db.scalar(pending_approvals_stmt) or 0

    total_approvals_stmt = select(func.count(RemediationApproval.id))
    total_approvals = await db.scalar(total_approvals_stmt) or 0

    # Executions statistics
    total_executions_stmt = select(func.count(RemediationExecution.id))
    total_executions = await db.scalar(total_executions_stmt) or 0

    exec_status_stmt = select(
        RemediationExecution.status, func.count(RemediationExecution.id)
    ).group_by(RemediationExecution.status)
    exec_status_res = await db.execute(exec_status_stmt)
    executions_by_status = {row[0]: row[1] for row in exec_status_res.all()}

    exec_mode_stmt = select(
        RemediationExecution.mode, func.count(RemediationExecution.id)
    ).group_by(RemediationExecution.mode)
    exec_mode_res = await db.execute(exec_mode_stmt)
    executions_by_mode = {row[0]: row[1] for row in exec_mode_res.all()}

    # Verifications statistics
    total_verifications_stmt = select(func.count(ExecutionVerification.id))
    total_verifications = await db.scalar(total_verifications_stmt) or 0

    v_outcome_stmt = select(
        ExecutionVerification.outcome, func.count(ExecutionVerification.id)
    ).group_by(ExecutionVerification.outcome)
    v_outcome_res = await db.execute(v_outcome_stmt)
    verifications_by_outcome = {row[0]: row[1] for row in v_outcome_res.all()}

    # Rollback assessments statistics
    total_rollback_stmt = select(func.count(RollbackAssessment.id))
    total_rollback_assessments = await db.scalar(total_rollback_stmt) or 0

    rb_readiness_stmt = select(
        RollbackAssessment.readiness_status, func.count(RollbackAssessment.id)
    ).group_by(RollbackAssessment.readiness_status)
    rb_readiness_res = await db.execute(rb_readiness_stmt)
    rollback_by_readiness = {row[0]: row[1] for row in rb_readiness_res.all()}

    # Incident creation trend (recent 10 incidents by date)
    recent_incidents_stmt = (
        select(Incident.created_at, Incident.severity)
        .order_by(Incident.created_at.desc())
        .limit(20)
    )
    recent_incidents_res = await db.execute(recent_incidents_stmt)
    trend: list[dict[str, Any]] = [
        {
            "timestamp": row[0].isoformat(),
            "date": row[0].strftime("%b %d %H:%M"),
            "severity": row[1],
        }
        for row in recent_incidents_res.all()
    ]

    # Prometheus telemetry check
    service_val: float | None = None
    monitoring_ok = False
    try:
        val = query_prometheus(QUERIES["service_up"], at=datetime.now(UTC))
        if val is not None:
            service_val = val
            monitoring_ok = True
    except PrometheusError:
        monitoring_ok = False

    grafana_url = "http://localhost:3000"

    return SystemOverviewResponse(
        total_incidents=total_incidents,
        open_incidents=open_incidents,
        incidents_by_severity=incidents_by_severity,
        incidents_by_status=incidents_by_status,
        pending_approvals=pending_approvals,
        total_approvals=total_approvals,
        total_executions=total_executions,
        executions_by_status=executions_by_status,
        executions_by_mode=executions_by_mode,
        total_verifications=total_verifications,
        verifications_by_outcome=verifications_by_outcome,
        total_rollback_assessments=total_rollback_assessments,
        rollback_by_readiness=rollback_by_readiness,
        service_availability=service_val,
        service_up=bool(service_val > 0) if service_val is not None else None,
        monitoring_available=monitoring_ok,
        grafana_url=grafana_url,
        incident_creation_trend=trend,
    )


@router.get("/overview/telemetry", response_model=list[TelemetryPoint])
async def get_service_telemetry_history(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    window_minutes: int = 30,
):
    """Retrieves service availability history from Prometheus for dashboard charts."""
    now = datetime.now(UTC)
    start = now - timedelta(minutes=max(5, min(window_minutes, 180)))
    try:
        samples = query_prometheus_range(
            QUERIES["service_up"],
            start=start,
            end=now,
            step="1m",
        )
        return [
            TelemetryPoint(
                timestamp=s.timestamp.strftime("%H:%M:%S"),
                value=s.value,
            )
            for s in samples
        ]
    except PrometheusError:
        return []


@router.get("/system/settings", response_model=SystemSettingsResponse)
async def get_system_settings(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
):
    """Returns non-sensitive system settings and current operator profile."""
    settings = get_settings()

    monitoring_ok = False
    try:
        val = query_prometheus(QUERIES["service_up"], at=datetime.now(UTC))
        monitoring_ok = val is not None
    except PrometheusError:
        monitoring_ok = False

    return SystemSettingsResponse(
        app_name=settings.app_name,
        environment=settings.environment,
        version="0.1.0",
        live_diagnostics_enabled=settings.live_diagnostics_enabled,
        prometheus_url=settings.prometheus_url,
        grafana_url="http://localhost:3000",
        monitoring_available=monitoring_ok,
        current_actor={
            "identity": actor.identity,
            "roles": sorted(actor.roles),
            "can_approve": actor.can_approve,
            "can_request": actor.can_request,
            "can_execute": actor.can_execute,
            "can_verify": actor.can_verify,
            "can_assess_rollback": actor.can_assess_rollback,
        },
    )
