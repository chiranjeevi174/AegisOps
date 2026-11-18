import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
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


class RollbackExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    EXECUTED = "executed"
    FAILED = "failed"


class RollbackExecution(Base):
    __tablename__ = "rollback_executions"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'executed', 'failed')",
            name="valid_rollback_execution_status",
        ),
        UniqueConstraint(
            "execution_id",
            "idempotency_key",
            name="uq_rollback_exec_idempotency_key",
        ),
        Index("ix_rollback_executions_assessment_id", "assessment_id"),
        Index("ix_rollback_executions_execution_id", "execution_id"),
        Index("ix_rollback_executions_incident_id", "incident_id"),
        Index("ix_rollback_executions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rollback_assessments.id", ondelete="RESTRICT"),
        nullable=False,
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

    operation_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=RollbackExecutionStatus.EXECUTED.value,
        nullable=False,
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
        nullable=False,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    duration_ms: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    restored_scenario: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    restored_state: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class RollbackExecutionEvent(Base):
    __tablename__ = "rollback_execution_events"

    __table_args__ = (
        Index("ix_rollback_execution_events_rb_exec_id", "rollback_execution_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    rollback_execution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rollback_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    execution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    actor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    previous_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    new_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    details: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
