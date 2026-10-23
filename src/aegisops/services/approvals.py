from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.core.config import get_settings
from aegisops.domain.approval import ApprovalStatus, RemediationApproval
from aegisops.domain.approval_event import ApprovalEvent, ApprovalEventType
from aegisops.domain.incident import Incident
from aegisops.services.incidents import IncidentNotFoundError
from aegisops.services.plan_integrity import (
    PlanIntegrityError,
    compute_plan_hash,
    verify_plan_integrity,
)
from aegisops.services.remediation_safety import validate_remediation_safety
from aegisops.workflows.remediation import RemediationPlan


class ApprovalNotFoundError(Exception):
    """Raised when an approval request does not exist."""


class ApprovalExpiredError(Exception):
    """Raised when attempting to decide an expired approval request."""


class InvalidApprovalStateError(Exception):
    """Raised when an illegal approval state transition is attempted."""


class SelfApprovalError(Exception):
    """Raised when the requesting actor attempts to approve their own remediation plan."""


class ApprovalValidationError(Exception):
    """Raised when input data for an approval request or decision is invalid."""


async def create_approval_request(
    session: AsyncSession,
    incident_id: UUID,
    plan: RemediationPlan | dict[str, Any],
    requested_by: str,
    validity_minutes: int | None = None,
    rca: dict[str, Any] | None = None,
) -> RemediationApproval:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise IncidentNotFoundError(f"Incident {incident_id} not found")

    # Safety validation of the remediation plan
    validated_plan = validate_remediation_safety(plan, rca=rca)

    # Invariants check
    if validated_plan.execution_enabled:
        raise ApprovalValidationError(
            "Cannot create approval for execution-enabled plan"
        )
    if not validated_plan.requires_human_approval:
        raise ApprovalValidationError(
            "Cannot create approval without mandatory human approval requirement"
        )

    snapshot = validated_plan.model_dump(mode="json")
    plan_hash = compute_plan_hash(snapshot)

    now = datetime.now(UTC)
    if validity_minutes is None:
        validity_minutes = get_settings().approval_validity_minutes
    expires_at = now + timedelta(minutes=validity_minutes)

    # Find maximum existing version for this incident
    max_version_stmt = select(
        func.coalesce(func.max(RemediationApproval.version), 0)
    ).where(RemediationApproval.incident_id == incident_id)
    max_version = await session.scalar(max_version_stmt) or 0
    new_version = max_version + 1

    # Check for existing pending request and supersede it atomically
    pending_stmt = (
        select(RemediationApproval)
        .where(
            RemediationApproval.incident_id == incident_id,
            RemediationApproval.status == ApprovalStatus.PENDING.value,
        )
        .with_for_update()
    )
    existing_pending = await session.scalar(pending_stmt)
    if existing_pending is not None:
        existing_pending.status = ApprovalStatus.SUPERSEDED.value
        existing_pending.decided_by = requested_by
        existing_pending.decided_at = now
        existing_pending.decision_reason = f"Superseded by version {new_version}"

        supersede_event = ApprovalEvent(
            approval_id=existing_pending.id,
            incident_id=incident_id,
            actor=requested_by,
            event_type=ApprovalEventType.SUPERSEDED.value,
            previous_status=ApprovalStatus.PENDING.value,
            new_status=ApprovalStatus.SUPERSEDED.value,
            reason=f"Superseded by newer remediation plan version {new_version}",
            plan_hash=existing_pending.plan_hash,
            created_at=now,
        )
        session.add(supersede_event)

    approval = RemediationApproval(
        incident_id=incident_id,
        plan_snapshot=snapshot,
        plan_hash=plan_hash,
        status=ApprovalStatus.PENDING.value,
        version=new_version,
        requested_by=requested_by,
        requested_at=now,
        expires_at=expires_at,
    )
    session.add(approval)
    await session.flush()

    create_event = ApprovalEvent(
        approval_id=approval.id,
        incident_id=incident_id,
        actor=requested_by,
        event_type=ApprovalEventType.CREATED.value,
        previous_status=None,
        new_status=ApprovalStatus.PENDING.value,
        reason=f"Created remediation approval request version {new_version}",
        plan_hash=plan_hash,
        created_at=now,
    )
    session.add(create_event)

    await session.commit()
    await session.refresh(approval)
    return approval


async def get_approval_request(
    session: AsyncSession,
    approval_id: UUID,
) -> RemediationApproval | None:
    return await session.get(RemediationApproval, approval_id)


async def list_approval_requests(
    session: AsyncSession,
    incident_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[RemediationApproval]:
    stmt = select(RemediationApproval).order_by(
        desc(RemediationApproval.requested_at),
        desc(RemediationApproval.id),
    )
    if incident_id is not None:
        stmt = stmt.where(RemediationApproval.incident_id == incident_id)
    if status is not None:
        stmt = stmt.where(RemediationApproval.status == status)

    stmt = stmt.limit(limit).offset(offset)
    result = await session.scalars(stmt)
    return list(result.all())


async def get_approval_events(
    session: AsyncSession,
    approval_id: UUID,
) -> list[ApprovalEvent]:
    stmt = (
        select(ApprovalEvent)
        .where(ApprovalEvent.approval_id == approval_id)
        .order_by(ApprovalEvent.created_at.asc())
    )
    result = await session.scalars(stmt)
    return list(result.all())


async def approve_request(
    session: AsyncSession,
    approval_id: UUID,
    actor_identity: str,
    comment: str | None = None,
) -> RemediationApproval:
    stmt = (
        select(RemediationApproval)
        .where(RemediationApproval.id == approval_id)
        .with_for_update()
    )
    approval = await session.scalar(stmt)
    if approval is None:
        raise ApprovalNotFoundError(f"Approval request {approval_id} not found")

    now = datetime.now(UTC)

    # Dynamic expiration check
    if approval.status == ApprovalStatus.PENDING.value and now >= approval.expires_at:
        approval.status = ApprovalStatus.EXPIRED.value
        approval.decided_at = now
        approval.decision_reason = "Request expired before human decision"
        session.add(
            ApprovalEvent(
                approval_id=approval.id,
                incident_id=approval.incident_id,
                actor="system",
                event_type=ApprovalEventType.EXPIRED.value,
                previous_status=ApprovalStatus.PENDING.value,
                new_status=ApprovalStatus.EXPIRED.value,
                reason="Expired due to validity timeout",
                plan_hash=approval.plan_hash,
                created_at=now,
            )
        )
        await session.commit()
        raise ApprovalExpiredError(f"Approval request {approval_id} has expired")

    # State validation
    if approval.status != ApprovalStatus.PENDING.value:
        raise InvalidApprovalStateError(
            f"Cannot approve request in '{approval.status}' status (must be 'pending')"
        )

    # Separation of duties check
    if (
        get_settings().enforce_separation_of_duties
        and approval.requested_by == actor_identity
    ):
        raise SelfApprovalError(
            f"Self-approval prohibited: requesting actor '{actor_identity}' cannot approve their own plan"
        )

    # Plan integrity check
    if not verify_plan_integrity(approval.plan_snapshot, approval.plan_hash):
        raise PlanIntegrityError(
            f"Plan integrity verification failed for approval request {approval_id}"
        )

    # Transition to approved
    previous_status = approval.status
    approval.status = ApprovalStatus.APPROVED.value
    approval.decided_by = actor_identity
    approval.decided_at = now
    approval.decision_reason = comment

    session.add(
        ApprovalEvent(
            approval_id=approval.id,
            incident_id=approval.incident_id,
            actor=actor_identity,
            event_type=ApprovalEventType.APPROVED.value,
            previous_status=previous_status,
            new_status=ApprovalStatus.APPROVED.value,
            reason=comment,
            plan_hash=approval.plan_hash,
            created_at=now,
        )
    )

    await session.commit()
    await session.refresh(approval)
    return approval


async def reject_request(
    session: AsyncSession,
    approval_id: UUID,
    actor_identity: str,
    reason: str,
) -> RemediationApproval:
    if not reason or len(reason.strip()) < 3:
        raise ApprovalValidationError(
            "A meaningful rejection reason is required (minimum 3 characters)"
        )

    stmt = (
        select(RemediationApproval)
        .where(RemediationApproval.id == approval_id)
        .with_for_update()
    )
    approval = await session.scalar(stmt)
    if approval is None:
        raise ApprovalNotFoundError(f"Approval request {approval_id} not found")

    now = datetime.now(UTC)

    # Dynamic expiration check
    if approval.status == ApprovalStatus.PENDING.value and now >= approval.expires_at:
        approval.status = ApprovalStatus.EXPIRED.value
        approval.decided_at = now
        approval.decision_reason = "Request expired before human decision"
        session.add(
            ApprovalEvent(
                approval_id=approval.id,
                incident_id=approval.incident_id,
                actor="system",
                event_type=ApprovalEventType.EXPIRED.value,
                previous_status=ApprovalStatus.PENDING.value,
                new_status=ApprovalStatus.EXPIRED.value,
                reason="Expired due to validity timeout",
                plan_hash=approval.plan_hash,
                created_at=now,
            )
        )
        await session.commit()
        raise ApprovalExpiredError(f"Approval request {approval_id} has expired")

    if approval.status != ApprovalStatus.PENDING.value:
        raise InvalidApprovalStateError(
            f"Cannot reject request in '{approval.status}' status (must be 'pending')"
        )

    if not verify_plan_integrity(approval.plan_snapshot, approval.plan_hash):
        raise PlanIntegrityError(
            f"Plan integrity verification failed for approval request {approval_id}"
        )

    previous_status = approval.status
    approval.status = ApprovalStatus.REJECTED.value
    approval.decided_by = actor_identity
    approval.decided_at = now
    approval.decision_reason = reason.strip()

    session.add(
        ApprovalEvent(
            approval_id=approval.id,
            incident_id=approval.incident_id,
            actor=actor_identity,
            event_type=ApprovalEventType.REJECTED.value,
            previous_status=previous_status,
            new_status=ApprovalStatus.REJECTED.value,
            reason=reason.strip(),
            plan_hash=approval.plan_hash,
            created_at=now,
        )
    )

    await session.commit()
    await session.refresh(approval)
    return approval


async def request_revision(
    session: AsyncSession,
    approval_id: UUID,
    actor_identity: str,
    reason: str,
) -> RemediationApproval:
    if not reason or len(reason.strip()) < 3:
        raise ApprovalValidationError(
            "A meaningful revision request reason is required (minimum 3 characters)"
        )

    stmt = (
        select(RemediationApproval)
        .where(RemediationApproval.id == approval_id)
        .with_for_update()
    )
    approval = await session.scalar(stmt)
    if approval is None:
        raise ApprovalNotFoundError(f"Approval request {approval_id} not found")

    now = datetime.now(UTC)

    if approval.status == ApprovalStatus.PENDING.value and now >= approval.expires_at:
        approval.status = ApprovalStatus.EXPIRED.value
        approval.decided_at = now
        approval.decision_reason = "Request expired before human decision"
        session.add(
            ApprovalEvent(
                approval_id=approval.id,
                incident_id=approval.incident_id,
                actor="system",
                event_type=ApprovalEventType.EXPIRED.value,
                previous_status=ApprovalStatus.PENDING.value,
                new_status=ApprovalStatus.EXPIRED.value,
                reason="Expired due to validity timeout",
                plan_hash=approval.plan_hash,
                created_at=now,
            )
        )
        await session.commit()
        raise ApprovalExpiredError(f"Approval request {approval_id} has expired")

    if approval.status != ApprovalStatus.PENDING.value:
        raise InvalidApprovalStateError(
            f"Cannot request revision for request in '{approval.status}' status (must be 'pending')"
        )

    if not verify_plan_integrity(approval.plan_snapshot, approval.plan_hash):
        raise PlanIntegrityError(
            f"Plan integrity verification failed for approval request {approval_id}"
        )

    previous_status = approval.status
    approval.status = ApprovalStatus.REVISION_REQUESTED.value
    approval.decided_by = actor_identity
    approval.decided_at = now
    approval.decision_reason = reason.strip()

    session.add(
        ApprovalEvent(
            approval_id=approval.id,
            incident_id=approval.incident_id,
            actor=actor_identity,
            event_type=ApprovalEventType.REVISION_REQUESTED.value,
            previous_status=previous_status,
            new_status=ApprovalStatus.REVISION_REQUESTED.value,
            reason=reason.strip(),
            plan_hash=approval.plan_hash,
            created_at=now,
        )
    )

    await session.commit()
    await session.refresh(approval)
    return approval


async def expire_stale_requests(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    stmt = (
        select(RemediationApproval)
        .where(
            RemediationApproval.status == ApprovalStatus.PENDING.value,
            RemediationApproval.expires_at <= now,
        )
        .with_for_update()
    )
    result = await session.scalars(stmt)
    stale_requests = list(result.all())

    count = 0
    for approval in stale_requests:
        approval.status = ApprovalStatus.EXPIRED.value
        approval.decided_at = now
        approval.decision_reason = "Expired due to validity timeout"
        session.add(
            ApprovalEvent(
                approval_id=approval.id,
                incident_id=approval.incident_id,
                actor="system",
                event_type=ApprovalEventType.EXPIRED.value,
                previous_status=ApprovalStatus.PENDING.value,
                new_status=ApprovalStatus.EXPIRED.value,
                reason="Expired due to validity timeout",
                plan_hash=approval.plan_hash,
                created_at=now,
            )
        )
        count += 1

    if count > 0:
        await session.commit()
    return count
