from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.api.approval_schemas import (
    ApprovalDetailResponse,
    ApprovalEventResponse,
    ApprovalResponse,
    ApproveRequest,
    DecisionResponse,
    RejectRequest,
    RevisionRequest,
)
from aegisops.core.auth import (
    AuthenticatedActor,
    get_approver_actor,
    get_current_actor,
    get_requester_actor,
)
from aegisops.core.rate_limit import rate_limit_decisions
from aegisops.db.session import get_db
from aegisops.domain.approval import ApprovalStatus
from aegisops.observability.metrics import APPROVAL_DECISIONS
from aegisops.services import approvals
from aegisops.services.approvals import (
    ApprovalExpiredError,
    ApprovalNotFoundError,
    ApprovalValidationError,
    InvalidApprovalStateError,
    SelfApprovalError,
)
from aegisops.services.incidents import IncidentNotFoundError, run_incident_workflow
from aegisops.services.plan_integrity import PlanIntegrityError
from aegisops.services.remediation_safety import RemediationSafetyError

router = APIRouter(tags=["Remediation Approvals"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/incidents/{incident_id}/approvals",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident_approval(
    incident_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_requester_actor)],
    db: DbSession,
):
    try:
        # Run workflow to produce and safety-validate the server-side remediation plan
        result = await run_incident_workflow(db, incident_id)
    except IncidentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    plan_dict = result.get("remediation_plan")
    error = result.get("remediation_error")

    if not plan_dict or error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create approval request: {error or 'No remediation plan available'}",
        )

    try:
        approval = await approvals.create_approval_request(
            session=db,
            incident_id=incident_id,
            plan=plan_dict,
            requested_by=actor.identity,
            rca=result.get("rca"),
        )
        return approval
    except (RemediationSafetyError, ApprovalValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/approvals",
    response_model=list[ApprovalResponse],
)
async def list_approvals(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
    incident_id: UUID | None = None,
    status_filter: Annotated[ApprovalStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await approvals.list_approval_requests(
        session=db,
        incident_id=incident_id,
        status=status_filter.value if status_filter else None,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/approvals/{approval_id}",
    response_model=ApprovalDetailResponse,
)
async def get_approval(
    approval_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
):
    approval = await approvals.get_approval_request(db, approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {approval_id} not found",
        )
    return approval


@router.get(
    "/approvals/{approval_id}/events",
    response_model=list[ApprovalEventResponse],
)
async def get_approval_events(
    approval_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
):
    approval = await approvals.get_approval_request(db, approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {approval_id} not found",
        )
    return await approvals.get_approval_events(db, approval_id)


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=DecisionResponse,
    dependencies=[Depends(rate_limit_decisions)],
)
async def approve_approval(
    approval_id: UUID,
    payload: ApproveRequest,
    actor: Annotated[AuthenticatedActor, Depends(get_approver_actor)],
    db: DbSession,
):
    try:
        approval = await approvals.approve_request(
            session=db,
            approval_id=approval_id,
            actor_identity=actor.identity,
            comment=payload.comment,
        )
        APPROVAL_DECISIONS.labels(decision="approved").inc()
        return DecisionResponse(
            approval_id=approval.id,
            incident_id=approval.incident_id,
            status=ApprovalStatus(approval.status),
            version=approval.version,
            plan_hash=approval.plan_hash,
            decided_by=actor.identity,
            decided_at=approval.decided_at or approval.requested_at,
            decision_reason=approval.decision_reason,
            requires_human_approval=True,
            execution_enabled=False,
        )
    except ApprovalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {approval_id} not found",
        )
    except SelfApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except (ApprovalExpiredError, InvalidApprovalStateError, PlanIntegrityError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=DecisionResponse,
    dependencies=[Depends(rate_limit_decisions)],
)
async def reject_approval(
    approval_id: UUID,
    payload: RejectRequest,
    actor: Annotated[AuthenticatedActor, Depends(get_approver_actor)],
    db: DbSession,
):
    try:
        approval = await approvals.reject_request(
            session=db,
            approval_id=approval_id,
            actor_identity=actor.identity,
            reason=payload.reason,
        )
        APPROVAL_DECISIONS.labels(decision="rejected").inc()
        return DecisionResponse(
            approval_id=approval.id,
            incident_id=approval.incident_id,
            status=ApprovalStatus(approval.status),
            version=approval.version,
            plan_hash=approval.plan_hash,
            decided_by=actor.identity,
            decided_at=approval.decided_at or approval.requested_at,
            decision_reason=approval.decision_reason,
            requires_human_approval=True,
            execution_enabled=False,
        )
    except ApprovalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {approval_id} not found",
        )
    except ApprovalValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except (ApprovalExpiredError, InvalidApprovalStateError, PlanIntegrityError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.post(
    "/approvals/{approval_id}/request-revision",
    response_model=DecisionResponse,
    dependencies=[Depends(rate_limit_decisions)],
)
async def request_revision_approval(
    approval_id: UUID,
    payload: RevisionRequest,
    actor: Annotated[AuthenticatedActor, Depends(get_approver_actor)],
    db: DbSession,
):
    try:
        approval = await approvals.request_revision(
            session=db,
            approval_id=approval_id,
            actor_identity=actor.identity,
            reason=payload.reason,
        )
        APPROVAL_DECISIONS.labels(decision="revision_requested").inc()
        return DecisionResponse(
            approval_id=approval.id,
            incident_id=approval.incident_id,
            status=ApprovalStatus(approval.status),
            version=approval.version,
            plan_hash=approval.plan_hash,
            decided_by=actor.identity,
            decided_at=approval.decided_at or approval.requested_at,
            decision_reason=approval.decision_reason,
            requires_human_approval=True,
            execution_enabled=False,
        )
    except ApprovalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {approval_id} not found",
        )
    except ApprovalValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except (ApprovalExpiredError, InvalidApprovalStateError, PlanIntegrityError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
