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


class RollbackEventType(StrEnum):
    REQUESTED = "requested"
    STARTED = "assessment_started"
    EVALUATED = "eligibility_evaluated"
    SIMULATED = "simulation_completed"
    COMPLETED = "assessment_completed"
    FAILED = "assessment_failed"


class RollbackEvent(Base):
    __tablename__ = "rollback_events"

    __table_args__ = (
        Index("ix_rollback_events_assessment_id", "assessment_id"),
        Index("ix_rollback_events_execution_id", "execution_id"),
        Index("ix_rollback_events_created_at", "created_at"),
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

    readiness_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
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
