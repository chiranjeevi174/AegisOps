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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from aegisops.db.base import Base


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class RemediationApproval(Base):
    __tablename__ = "remediation_approvals"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'revision_requested', 'expired', 'superseded')",
            name="valid_approval_status",
        ),
        CheckConstraint(
            "version > 0",
            name="valid_approval_version",
        ),
        UniqueConstraint(
            "incident_id",
            "version",
            name="uq_incident_approval_version",
        ),
        Index(
            "uq_active_pending_approval_per_incident",
            "incident_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_remediation_approvals_incident_id", "incident_id"),
        Index("ix_remediation_approvals_status", "status"),
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

    plan_snapshot: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )

    plan_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=ApprovalStatus.PENDING.value,
        nullable=False,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    requested_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    decided_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    decision_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
