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


class RollbackReadinessStatus(StrEnum):
    READY_FOR_REVIEW = "ready_for_review"
    BLOCKED = "blocked"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_APPLICABLE = "not_applicable"


class RollbackApplicability(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    APPLICABLE = "applicable"
    UNSUPPORTED = "unsupported"


class RollbackRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RollbackAssessmentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RollbackAssessment(Base):
    __tablename__ = "rollback_assessments"

    __table_args__ = (
        CheckConstraint(
            "readiness_status IN ('ready_for_review', 'blocked', 'insufficient_evidence', 'not_applicable')",
            name="valid_rollback_readiness_status",
        ),
        CheckConstraint(
            "applicability IN ('not_applicable', 'applicable', 'unsupported')",
            name="valid_rollback_applicability",
        ),
        CheckConstraint(
            "risk_level IN ('low', 'medium', 'high')",
            name="valid_rollback_risk_level",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="valid_rollback_assessment_status",
        ),
        CheckConstraint(
            "rollback_execution_enabled = FALSE",
            name="ck_rollback_execution_disabled",
        ),
        CheckConstraint(
            "human_authorization_required = TRUE",
            name="ck_rollback_human_auth_required",
        ),
        CheckConstraint(
            "system_changes_performed = FALSE",
            name="ck_rollback_system_changes_disabled",
        ),
        UniqueConstraint(
            "execution_id",
            "idempotency_key",
            name="uq_rollback_assessment_idempotency_key",
        ),
        Index("ix_rollback_assessments_execution_id", "execution_id"),
        Index("ix_rollback_assessments_incident_id", "incident_id"),
        Index("ix_rollback_assessments_approval_id", "approval_id"),
        Index("ix_rollback_assessments_readiness_status", "readiness_status"),
        Index("ix_rollback_assessments_status", "status"),
        Index("ix_rollback_assessments_created_at", "requested_at"),
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
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=RollbackAssessmentStatus.RUNNING.value,
        nullable=False,
    )

    readiness_status: Mapped[str] = mapped_column(
        String(30),
        default=RollbackReadinessStatus.NOT_APPLICABLE.value,
        nullable=False,
    )

    applicability: Mapped[str] = mapped_column(
        String(30),
        default=RollbackApplicability.NOT_APPLICABLE.value,
        nullable=False,
    )

    risk_level: Mapped[str] = mapped_column(
        String(20),
        default=RollbackRiskLevel.LOW.value,
        nullable=False,
    )

    assessment_data: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    simulation_result: Mapped[dict | None] = mapped_column(
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

    human_authorization_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    rollback_execution_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    system_changes_performed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
