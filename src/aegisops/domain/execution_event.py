import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from aegisops.db.base import Base


class ExecutionEventType(StrEnum):
    REQUESTED = "requested"
    SIMULATION_STARTED = "simulation_started"
    SIMULATION_COMPLETED = "simulation_completed"
    SIMULATION_FAILED = "simulation_failed"
    DIAGNOSTIC_STARTED = "diagnostic_started"
    DIAGNOSTIC_COMPLETED = "diagnostic_completed"
    DIAGNOSTIC_FAILED = "diagnostic_failed"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"


class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    __table_args__ = (
        Index("ix_execution_events_execution_id", "execution_id"),
        Index("ix_execution_events_incident_id", "incident_id"),
        Index("ix_execution_events_approval_id", "approval_id"),
        Index("ix_execution_events_created_at", "created_at"),
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

    operation_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    approved_plan_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    details: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
