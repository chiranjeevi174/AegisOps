import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from aegisops.db.base import Base


class VerificationOutcome(StrEnum):
    DIAGNOSTIC_VERIFIED = "diagnostic_verified"
    INCONCLUSIVE = "inconclusive"
    VERIFICATION_FAILED = "verification_failed"
    NOT_APPLICABLE = "not_applicable"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class ExecutionVerification(Base):
    __tablename__ = "execution_verifications"

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('diagnostic_verified', 'inconclusive', 'verification_failed', 'not_applicable')",
            name="valid_verification_outcome",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'timed_out')",
            name="valid_verification_status",
        ),
        UniqueConstraint(
            "execution_id",
            "idempotency_key",
            name="uq_execution_verification_idempotency_key",
        ),
        Index("ix_execution_verifications_execution_id", "execution_id"),
        Index("ix_execution_verifications_incident_id", "incident_id"),
        Index("ix_execution_verifications_approval_id", "approval_id"),
        Index("ix_execution_verifications_outcome", "outcome"),
        Index("ix_execution_verifications_status", "status"),
        Index("ix_execution_verifications_created_at", "requested_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    execution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("remediation_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("incidents.id", ondelete="RESTRICT"),
        nullable=False,
    )

    approval_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("remediation_approvals.id", ondelete="RESTRICT"),
        nullable=False,
    )

    approved_plan_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    operation_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    execution_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=VerificationStatus.RUNNING.value,
        nullable=False,
    )

    outcome: Mapped[str] = mapped_column(
        String(30),
        default=VerificationOutcome.INCONCLUSIVE.value,
        nullable=False,
    )

    verification_criteria: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    baseline_evidence: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    followup_evidence: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    metric_comparison: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    limitations: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )

    observations: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )

    requested_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    duration_ms: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    human_review_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    remediation_success_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
