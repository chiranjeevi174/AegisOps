import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from aegisops.db.base import Base


class Incident(Base):
    __tablename__ = "incidents"

    __table_args__ = (
        CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="valid_incident_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'investigating', 'resolved')",
            name="valid_incident_status",
        ),
        UniqueConstraint(
            "alert_fingerprint",
            name="uq_incidents_alert_fingerprint",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="open")
    source: Mapped[str] = mapped_column(String(100), default="manual")

    alert_fingerprint: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    alert_state: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    alert_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    alert_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
