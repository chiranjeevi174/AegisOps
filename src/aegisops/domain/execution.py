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


class ExecutionMode(StrEnum):
    SIMULATION = "simulation"
    LIVE_DIAGNOSTIC = "live_diagnostic"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SIMULATED = "simulated"
    DIAGNOSED = "diagnosed"
    FAILED = "failed"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"


class RemediationExecution(Base):
    __tablename__ = "remediation_executions"

    __table_args__ = (
        CheckConstraint(
            "mode IN ('simulation', 'live_diagnostic')",
            name="valid_execution_mode",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'simulated', 'diagnosed', 'failed', 'rejected', 'timed_out')",
            name="valid_execution_status",
        ),
        UniqueConstraint(
            "approval_id",
            "idempotency_key",
            name="uq_approval_idempotency_key",
        ),
        Index("ix_remediation_executions_incident_id", "incident_id"),
        Index("ix_remediation_executions_approval_id", "approval_id"),
        Index("ix_remediation_executions_operation_id", "operation_id"),
        Index("ix_remediation_executions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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

    approved_plan_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    selected_recommendation_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    selected_recommendation_title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    operation_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    parameters: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )

    requested_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    mode: Mapped[str] = mapped_column(
        String(20),
        default=ExecutionMode.SIMULATION.value,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=ExecutionStatus.SIMULATED.value,
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

    simulation_result: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    diagnostic_result: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    duration_ms: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
